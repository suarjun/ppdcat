#! /usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
from Start_multi_datetime import app
import threading
#import inspect
#import ctypes
import select
import socket
import heapq  # 实现最小堆模块
import copy
import time
import ssl

'''
select.epoll(sizehint=-1, flags=0)    创建epoll对象
epoll.close()                         关闭epoll对象的文件描述符
epoll.closed                          检测epoll对象是否关闭
epoll.fileno()                        返回epoll对象的文件描述符数量
epoll.fromfd(fd)                      根据指定的文件描述符创建epoll对象
epoll.register(fd[, eventmask])       向epoll对象中注册文件描述符和对应的事件
epoll.modify(fd, eventmask)           修改注册
epoll.unregister(fd)                  取消注册
epoll.poll(timeout=-1, maxevents=-1)  阻塞，直到注册的文件描述符所绑定的事件发生,会返回一个dict，格式为：{(f

select 事件常量       意义   pycurl 事件数
1  EPOLLIN        读就绪    1
4  EPOLLOUT       写就绪    2
2  EPOLLPRI       有数据紧急读取
8  EPOLLERR       assoc. fd有错误情况发生
16 EPOLLHUP       assoc. fd发生挂起
2147483648 EPOLLET        设置边缘触发(ET)（默认的是水平触发）
1073741824 EPOLLONESHOT   设置为 one-short 行为，一个事件(event)被拉出后，对应的fd在内部被禁用
64 EPOLLRDNORM    和 EPOLLIN 相等
128 EPOLLRDBAND    优先读取的数据带(data band)
256 EPOLLWRNORM    和 EPOLLOUT 相等
512 EPOLLWRBAND    优先写的数据带(data band)
1024 EPOLLMSG       忽视
'''

class Loop(object):
    __slots__ = ['epoll', 'free_sockets', 'fileno_socket', 'active_sockets', 'epoll_delay', 'gen', 'gen_list', 'gen_loop', 'next_gen_loop', 'next_gen_periodic', 'next_gen_socket_closed', 'timer', 'timer_thread', 'max_active_sockets', 'timeout', 'gen_deley_difference', 'loop_host_dict']

    def __init__(self, connect_timeout=20, epoll_delay=0.0001):
        self.epoll = select.epoll()
        self.free_sockets = defaultdict(list)
        self.active_sockets = defaultdict(set)
        self.fileno_socket = {}
        self.epoll_delay = epoll_delay
        self.gen = []
        self.gen_list = set()
        self.gen_loop = {}
        self.loop_host_dict = {}
        self.next_gen_loop = set()
        self.next_gen_periodic = set()
        self.next_gen_socket_closed = set()
        self.max_active_sockets = 10
        self.timeout = 10

    def add_future(self, gen):
        try:
            self.gen_list.add(gen)
            self.gen.append(gen)
            gen.send(None)
        except StopIteration:
            self.gen_list.remove(gen)
            self.gen.pop()

    def send_gen(self, gen, value=None):
        try:
            self.gen.append(gen)
            gen.send(value)
        except StopIteration:
            self.gen_list.remove(gen)
            self.gen.pop()
        except UnicodeDecodeError:
            self.send_gen(gen, '')

    def add_future_loop(self, delay, gen, loop_host, create_free_sockets, min_free_sockets, max_free_sockets):
        if self.gen_loop.get(delay):
            self.gen_loop[delay].add(gen)
        else:
            self.gen_loop[delay] = {gen}
        self.loop_host_dict[loop_host] = {'create_free_sockets':create_free_sockets, 'min_free_sockets':min_free_sockets, 'max_free_sockets':max_free_sockets}
        for i in range(create_free_sockets):
           self.create_socket(loop_host)

    def request(self, host=None, url=None, headers=[], data=None, timeout=20, after_idle_sec=1, interval_sec=3, max_fails=5):
        if self.free_sockets[host]:
            ssock = self.free_sockets[host].pop(0)
            ssock.gen = self.gen.pop()
            if self._send_data(ssock, url, host, headers, data):
                self.epoll.register(ssock.fileno(), select.EPOLLIN |select.EPOLLERR | select.EPOLLET)
        else:
            ssock = self.create_socket(host)
            if ssock:
                ssock.gen = self.gen.pop()
                ssock.dict_post = {'url':url, 'headers':headers, 'data':data}
            else:
                self.next_gen_socket_closed.add((self.gen.pop(), ''))

    def create_socket(self, host, after_idle_sec=1, interval_sec=3, max_fails=5):
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 禁用 Nagle 算法，减少延迟
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # 在客户端开启心跳维护
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)  # 设置连接上如果没有数据发送的话，多久后发送keepalive探测分组，单位是秒
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)  # 前后两次探测之间的时间间隔，单位是秒
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)  # 关闭一个非活跃连接之前的最大重试次数
        context = ssl.create_default_context()
        ssock = context.wrap_socket(sock,server_hostname=host)
        ssock.host = host
        ssock.cookie = None
        try:
            ssock.connect((host, 443))
        except (socket.timeout, TimeoutError):
            print('连接超时错误')
            ssock.shutdown(2)
            ssock.close()
            return None
        else:
            ssock.setblocking(False)
            ssock.startime = time.time()
            self.active_sockets[host].add(ssock)
            fileno = ssock.fileno()
            self.fileno_socket[fileno] = ssock
            self.epoll.register(fileno, select.EPOLLOUT |select.EPOLLERR | select.EPOLLET)
            return ssock

    def _send_data(self, ssock, url, host, headers, data):
        fileno = ssock.fileno()
        headers = ''.join(headers)
        data = f"POST {url} HTTP/1.1\r\nHost:{host}\r\nContent-Length:{len(data)}\r\n{headers+ssock.cookie if 'Cookie' not in headers and ssock.cookie else headers}\r\n{data}".encode()
        try:
            ssock.sendall(data)  # BrokenPipeError
            return True
        except (OSError, BrokenPipeError):
            #print('发送管道错误', ssock.gen)
            self.next_gen_socket_closed.add((ssock.gen, False))
            ssock.close()
            return False
        except (socket.timeout, TimeoutError):
            print('发送超时错误', ssock)
            self.next_gen_socket_closed.add((ssock.gen, ''))
            ssock.shutdown(2)
            ssock.close()
            return False

    def await_sleep(self, delay):
        self.timer.add(self.gen.pop(), time.time()+delay)

    def _result_worker(self, fileno, sock, gen, first_data, value=''):
        if b'keep-alive' in first_data:
            self.free_sockets[sock.host].append(sock)
            self.epoll.unregister(fileno)
            self.send_gen(gen, value=value)
        else:
            #print('服务器端关闭')
            self.send_gen(gen, value=value)
            self.epoll.unregister(fileno)
            del self.fileno_socket[fileno]
            sock.shutdown(2)
            sock.close()

    def _loop(self):
        events = self.epoll.poll(self.epoll_delay)
        for fileno, event in events:
            sock = self.fileno_socket[fileno]
            #print('事件', fileno, event)
            if event & select.EPOLLIN:
                gen = sock.gen
                try:
                    first_data = sock.recv(530)
                    #print('读取', first_data, sock)
                except (OSError, socket.timeout, TimeoutError):
                    print('预读取超时错误', fileno)
                    self._result_worker(fileno, sock, gen, b'')
                else:
                    if first_data:
                        if first_data[9:12] == b'200':
                            if b'Set-Cookie' in first_data:
                                sock.cookie = f"Cookie:{first_data.split(b'Set-Cookie: ', 1)[1].split(b'; Path', 1)[0].decode()}\r\n"
                            buffer = first_data
                            #print('读取', sock, first_data.decode())
                            if b'chunked' in first_data:
                                SSLWantReadError_times = 0
                                while 1:
                                    try:
                                        data = sock.recv(2048)  # 阻塞模式下，从可读文件描述符读取到空数据，会引发 BlockIOError 错误，而非阻塞模式下，会引发 ssl.SSLWantReadError 读取错误
                                        #print('读取',data)
                                    except ssl.SSLWantReadError:
                                        #print('块读取SSLWantReadError错误')
                                        SSLWantReadError_times += 1
                                        if SSLWantReadError_times > 100000:
                                            #print('块读取SSLWantReadError错误达到上限', buffer)
                                            self._result_worker(fileno, sock, gen, b'')
                                            break
                                        else:
                                            continue
                                    except (OSError, socket.timeout, TimeoutError):
                                        print('chunked 超时错误', sock)
                                        self._result_worker(fileno, sock, gen, b'')
                                        break
                                    else:
                                        if data[-5:] == b'0\r\n\r\n':
                                            buffer += data[:-5]
                                            body = buffer.split(b'\r\n\r\n' , 1)
                                            self._result_worker(fileno, sock, gen, first_data, value=b''.join(body[1].split(b'\r\n')[1::2]).decode(errors='replace'))
                                            break
                                        else:
                                            buffer += data
                            else:
                                size = int(first_data.split(b'Content-Length: ', 1)[1].split(b'\r\n', 1)[0])
                                body = buffer.split(b'\r\n\r\n', 1)[1]
                                if size > len(body):
                                    size -= len(body)
                                    while size:
                                        try:
                                            data = sock.recv(size)
                                            #print('读取', sock, data.decode())
                                        except ssl.SSLWantReadError:
                                            pass
                                        except (OSError, socket.timeout, TimeoutError):
                                            print('Content-Length 超时错误', fileno)
                                            self._result_worker(fileno, sock, gen, b'')
                                            break
                                        else:
                                            body += data
                                            size -= len(data)
                                    else:
                                        self._result_worker(fileno, sock, gen, first_data, value=body.decode(errors='replace'))
                                else:
                                    self._result_worker(fileno, sock, gen, first_data, value=body.decode(errors='replace'))
                        elif first_data[9:12] == b'502':
                            #print('502错误', fileno, first_data)
                            if b'keep-alive' in first_data:
                                try:
                                    sock.recv(1024)
                                except (ssl.SSLWantReadError, OSError):
                                    pass
                                self.free_sockets[sock.host].append(sock)
                            else:
                                del self.fileno_socket[fileno]
                                sock.shutdown(2)
                                sock.close()
                            self.epoll.unregister(fileno)
                            self.send_gen(gen, value='')
                        else:
                            #print('其他错误', fileno, first_data)
                            self.send_gen(gen, value='')
                            del self.fileno_socket[fileno]
                            self.epoll.unregister(fileno)
                            sock.close()
                    else:
                        print('接收空', fileno)
                        self.epoll.unregister(fileno)
                        self.send_gen(gen, '')
                        del self.fileno_socket[fileno]
                        sock.close()
            elif event & select.EPOLLOUT:
                self.active_sockets[sock.host].remove(sock)
                if getattr(sock, 'dict_post', None):
                    self._send_data(sock, sock.dict_post['url'], sock.host, sock.dict_post['headers'], sock.dict_post['data'])
                    del sock.dict_post
                    self.epoll.modify(fileno, select.EPOLLIN |select.EPOLLERR | select.EPOLLET)  # select.EPOLLIN：水平模式，select.EPOLLIN | select.EPOLLET：边缘模式
                else:
                    self.epoll.unregister(fileno)
                    self.free_sockets[sock.host].append(sock)
            elif event & select.EPOLLERR:
                print('文件描述符错误', fileno)
                self.epoll.unregister(fileno)
                self.send_gen(gen, '')
                del self.fileno_socket[fileno]
                sock.shutdown(2)
                sock.close()

    def run_until_complete(self):
        self._run_timer()
        while 1:
            self._loop()
            if self.next_gen_periodic:
                self.send_gen(self.next_gen_periodic.pop())
            if not self.timer.periodic_handlers and not self.gen_list:
                self.epoll.close()
                for socks in self.active_sockets.values():
                    for sock in socks:
                        sock.shutdown(2)
                        sock.close()
                for socks in self.free_sockets.values():
                    for sock in socks:
                        sock.shutdown(2)
                        sock.close()
                break

    def run_forever(self):
        deley_sort = list(self.gen_loop.keys())
        deley_sort.sort()
        deley_new = deley_sort[:-1]
        deley_new.insert(0, 0)
        deley_difference = [v-vv for v,vv in zip(deley_sort, deley_new)]
        self.gen_deley_difference = [(self.gen_loop[delay], deley_difference[i]) for i,delay in enumerate(deley_sort)]

        self._run_timer()
        while 1:
            for i in range(100):
                self._loop()
                while self.next_gen_loop:
                    next(self.next_gen_loop.pop())
                for host, value in self.loop_host_dict.items():
                    if value['min_free_sockets'] > len(self.free_sockets[host]):
                        #print('空闲套接字太少', len(self.free_sockets[host]))
                        for i in range(value['create_free_sockets'] - len(self.free_sockets[host])):
                            self.create_socket(host)
                    elif len(self.free_sockets[host]) > value['max_free_sockets']:
                        #print('空闲套接字太多', len(self.free_sockets[host]))
                        for i in range(len(self.free_sockets[host]) - value['max_free_sockets']):
                            sock = self.free_sockets[host].pop(0)
                            sock.shutdown(2)
                            sock.close()
            for host, sockets in self.active_sockets.items():
                    if len(sockets) > self.max_active_sockets:
                        socks = copy.copy(sockets)
                        now = time.time()
                        #print(host, '连接数过大')
                        for sock in socks:
                            if now - sock.startime > self.timeout:
                                self.epoll.unregister(sock.fileno())
                                sock.shutdown(2)
                                sock.close()
                                if getattr(sock, 'gen', None):
                                    self.next_gen_socket_closed.add((sock.gen, ''))
                                self.active_sockets[host].remove(sock)
            if self.next_gen_periodic:
                self.send_gen(self.next_gen_periodic.pop())
            if self.next_gen_socket_closed:
                gen, value = self.next_gen_socket_closed.pop()
                self.send_gen(gen, value=value)
            

    def _run_timer(self):
        self.timer = _Timer(self)
        self.timer_thread = threading.Thread(target=self.timer.run,args=())
        self.timer_thread.setDaemon(True)
        self.timer_thread.start()


'''def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("无效的线程ID")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc 失败")

def _stop_thread(thread):
    _async_raise(thread.ident, SystemExit)
    #print('成功销毁线程')'''


class _Timer(object):
    __slots__ = ['periodic_handlers', 'loop']

    def __init__(self, loop):
        self.periodic_handlers = []
        self.loop = loop

    def add(self, gen, deadline):
        heapq.heappush(self.periodic_handlers, _TimeHandler(gen, deadline))

    def run(self):
        if self.loop.gen_loop:
            while 1:
                for i in range(10):
                    for set_gen, delay in self.loop.gen_deley_difference:
                        self.loop.next_gen_loop.update(set_gen)
                        time.sleep(delay)
                if self.periodic_handlers and self.periodic_handlers[0].deadline <= time.time():
                    self.loop.next_gen_periodic.add(heapq.heappop(self.periodic_handlers).gen)
        else:
            while 1:
                time.sleep(1)
                if self.periodic_handlers:
                    if self.periodic_handlers[0].deadline <= time.time():
                        self.loop.send_gen(heapq.heappop(self.periodic_handlers).gen)
                elif not self.loop.fileno_socket:break

class _TimeHandler(object):
    __slots__ = ['gen', 'deadline']

    def __init__(self, gen, deadline):
        self.gen = gen
        self.deadline = deadline

    def __lt__(self, other):
        return self.deadline < other.deadline