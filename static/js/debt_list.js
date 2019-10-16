function gotoPage(a, page, policy_name, start_date, end_date, total_page)
    {$.post("/account/debt-list/{{ current_user.Name }}",
        {offset:20*(page-1),
            policy_name:policy_name,
            start_date:start_date,
            end_date:end_date,
            current_page:page,
            total_page:total_page
        },
        function(data,status){
            var data_json = JSON.parse(data);
            record_list = data_json["record_list"]["record_list"]
            policy_name = ", '"+data_json["record_list"]["policy_name"]+"'";
            start_date = ", '"+data_json["record_list"]["start_date"]+"'";
            end_date = ", '"+data_json["record_list"]["end_date"]+"'";
            current_page = data_json["record_list"]["current_page"];
            total_page = data_json["record_list"]["total_page"];
            replaceList(record_list);
            replaceGagination(policy_name, start_date, end_date, current_page, total_page);
            });
    };

function replaceList(record_list)
    {var tbody =$("tbody");
    tbody.empty();
    record_list.forEach(function(record){
        tbody.append('<tr id="list"><td style="text-align:center;">'+record["PolicyName"]+'</td><td style="text-align:center;"><a class=url href="https://invest.ppdai.com/loan/info/'+record["ListingId"]+'" target=_blank>'+record["ListingId"]+'</a></td><td style="text-align:center;">'+record["PriceForSaleRate"]+'</td><td style="text-align:center;">'+record["PriceForSale"]+'</td><td style="text-align:center;">'+record["BuyDate"]+'</td>')
        });
    };

function replaceGagination(policy_name, start_date, end_date, current_page, total_page)
    {var total_page_str = ", '"+total_page+"'";
    var pagination_html = '';
    if (current_page == 1)
        {pagination_html += '<li class="disabled"><a>&laquo;</a></li>';}
    else
        {pagination_html += '<li><a href="javascript:void(0);" onclick="gotoPage(this,'+(current_page-1)+policy_name+start_date+end_date+total_page_str+')">&laquo;</a></li>';}

    var prev = 0;
    for (var i = 1; i <= total_page; i ++)
        {if (1 <= i <= 2 || -1 <= i-total_page <= 0 || -1 <= i-current_page <= 4)
            {prev = i;
            if (i == current_page)
                {pagination_html += ('<li class="active"><a href="javascript:void(0);" onclick="gotoPage(this,'+i+policy_name+start_date+end_date+total_page_str+')">'+i+'</a></li>');}
            else
                {pagination_html += ('<li><a href="javascript:void(0);" onclick="gotoPage(this,'+i+policy_name+start_date+end_date+total_page_str+')">'+i+'</a></li>');}
            }
        else if (prev == i-1)
            {alert(i);
            pagination_html += '<li class="disabled"><a>…</a></li>';}
        }

    if (current_page == total_page)
        {pagination_html += '<li class="disabled"><a>&raquo;</a></li>';}
    else
        {pagination_html += ('<li><a href="javascript:void(0);" onclick="gotoPage(this,'+(current_page+1)+policy_name+start_date+end_date+total_page_str+')">&raquo;</a></li>');}

    $("ul.pagination").html(pagination_html);
    };

var iframe = document.getElementById("id_iframe");
iframe.onload = function() {
    var bodycontent=iframe.contentDocument.body.innerHTML;
    var jsonobj = JSON.parse(bodycontent);
    for (k in jsonobj)
        {if (k != 'record_list')
            {jsonobj[k].forEach(function(element) {
                $("form").before("<div class='alert alert-"+k+" fade in'><button type=button class=close data-dismiss=alert>×</button>"+element+"</div>");
                });
            }
        else
            {var record_list = jsonobj[k]["record_list"]
            var policy_name = ", '"+jsonobj[k]["policy_name"]+"'";
            var start_date = ", '"+jsonobj[k]["start_date"]+"'";
            var end_date = ", '"+jsonobj[k]["end_date"]+"'";
            var count = jsonobj[k]["count"];
            var limit = jsonobj[k]["limit"];
            var current_page = jsonobj[k]["current_page"];
            var total_page = Math.ceil(count/limit);
            var pagination_html = ''

            $("#count").text(count);

            replaceList(record_list);
            replaceGagination(policy_name, start_date, end_date, current_page, total_page);
            }
        }
    window.setTimeout(function(){
        $('[data-dismiss="alert"]').alert('close');
    },5000)
}