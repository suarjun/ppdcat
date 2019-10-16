function replaceList(record_list)
    {var num_tr = 0;
    var length_record_list= record_list.length;
    $("tr#list").each(function(){
        var tds = $(this).children("td");
        if ((num_tr+1) > length_record_list)
            {tds.filter("#PolicyName").html('<td style="text-align:center;" id="PolicyName">&emsp;</td>');
            tds.filter("#ListingId").text("");
            tds.filter("#ParticipationAmount").text("");
            tds.filter("#PriceForSaleRate").text("");
            tds.filter("#PriceForSale").text("");
            tds.filter("#BidTime").text("");
            tds.filter("#BuyDate").text("");
            }
        else
            {tds.filter("#PolicyName").text(record_list[num_tr]["PolicyName"]);
            tds.filter("#ListingId").html('<a class=url href="https://invest.ppdai.com/loan/info/'+record_list[num_tr]["ListingId"]+'" target=_blank>'+record_list[num_tr]["ListingId"]+'</a>');
            tds.filter("#ParticipationAmount").text(record_list[num_tr]["ParticipationAmount"]);
            tds.filter("#PriceForSaleRate").text(record_list[num_tr]["PriceForSaleRate"]);
            tds.filter("#PriceForSale").text(record_list[num_tr]["PriceForSale"]);
            tds.filter("#BidTime").text(record_list[num_tr]["BidTime"]);
            tds.filter("#BuyDate").text(record_list[num_tr]["BuyDate"]);
            num_tr += 1;
            }
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

function toIframe()
    {iframe = document.getElementById("id_iframe");
    alert('11');
    alert(iframe.contentDocument.body.innerHTML);}

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