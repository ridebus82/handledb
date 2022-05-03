import os
from datetime import datetime, timedelta
from itertools import chain

from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateformat import DateFormat

import json
import random
import re

from django.contrib import messages
from django.db.models import Q, Sum
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import render

# Create your views here.
from django.urls import reverse, reverse_lazy

from accountapp.models import User
from allmanageapp.models import AllManage
from dbmanageapp.models import MarketingList, UploadDbName, UploadDb, DbSetting, DbMemo, PaidList
from openpyxl import load_workbook

from dateutil.relativedelta import *


@login_required
def dbmainpage(request):
    q = Q()
    j = Q()
    if not request.user.rete == 'A':
        q.add(Q(db_manager=request.user), q.AND)
        j.add(Q(db_manager=request.user), q.AND)

    now_datetime = datetime.today()
    f_datetime = datetime(now_datetime.year, now_datetime.month, 1)

    last_month_first = datetime(now_datetime.year, now_datetime.month, 1) + relativedelta(months=-1)
    last_month_last = datetime(now_datetime.year, now_datetime.month, 1) + relativedelta(seconds=-1)

    now_month_setdate = set_search_day(f_datetime, now_datetime)
    last_month_setdate = set_search_day(last_month_first, last_month_last)

    q.add(Q(db_date__range=[now_month_setdate[0], now_month_setdate[1]]), q.AND)
    j.add(Q(db_date__range=[last_month_setdate[0], last_month_setdate[1]]), q.AND)

    now_month_price = UploadDb.objects.filter(q)
    last_month_price = UploadDb.objects.filter(j)

    n_sales = now_month_price.aggregate(Sum('db_paidprice'))
    l_sales = last_month_price.aggregate(Sum('db_paidprice'))
    n_sales = n_sales['db_paidprice__sum']
    l_sales = l_sales['db_paidprice__sum']

    if not n_sales or not l_sales:
        growth_per = None
    else:
        growth_per = "%.2f%%" % (n_sales / l_sales * 100.0)

    return render(request, 'dbmanageapp/mainpage.html', {'n_sales': n_sales, 'l_sales': l_sales, 'growth_per': growth_per})


@login_required
def base_setting(request):
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        upload_img = request.FILES.get('logo_image')
        ds_status = request.POST.get('ds_status')
        ds_statusbase = request.POST.get('ds_statusbase')
        theme_status = request.POST.get('theme_status')
        set_model = DbSetting.objects.last()

        print()

        if set_model:
            set_model.company_name = company_name
            set_model.ds_status = ds_status
            set_model.ds_statusbase = ds_statusbase
            set_model.theme_status = theme_status
            if upload_img:
                if set_model.logo_image:
                    os.remove(set_model.logo_image.path)
                set_model.logo_image = upload_img
            set_model.save()
            messages.success(request, '성공적으로 반영되었습니다.')
        else:
            dbset = DbSetting()
            dbset.company_name = company_name
            dbset.ds_status = ds_status
            dbset.ds_statusbase = ds_statusbase
            dbset.theme_status = theme_status
            if upload_img:
                dbset.logo_image = upload_img
            dbset.save()

    try:
        set_content = DbSetting.objects.last()
        select_menu = set_content.ds_status
        select_menu = select_menu.split(',')
        ontm = set_content.theme_status
    except:
        ontm = ""
        select_menu = ""
    return render(request, 'dbmanageapp/base_setting.html',
                  {'set_content': set_content, 'select_menu': select_menu, 'ot': ontm})


def marketer_stats(request):
    # 마케팅 리스트 에러 처리 (초기값 셋팅 X)
    try:
        marketing_list = MarketingList.objects.all()
    except:
        error = '마케팅 리스트를 추가해주세요!'
        return render(request, 'dbmanageapp/alldblist.html', {'error': error})

    q = Q()
    j = Q()
    geton = get_getlist(request, q, j)

    mk_list = MarketingList.objects.all()
    mk_list_value = MarketingList.objects.values()
    ii = 0
    mk_on_list = []

    for mlist in mk_list:
        paid_a_sum = 0

        mk_on_list.append(mk_list_value[ii])
        # 검색된 날짜 기준에 등록된 DB의 전체 리스트 (전체 등록건)
        all_dblist = mlist.dbmkname.filter(db_date__range=[geton['set_date'][0], geton['set_date'][1]])

        # 검색된 날짜 기준에 등록된 DB이름에 기재된 DB 값들의 합
        seach_dbname_for_spend_db = mlist.mkdname.filter(dbn_date__range=[geton['set_date'][0], geton['set_date'][1]])
        spend_db = seach_dbname_for_spend_db.aggregate(Sum('dbn_price'))

        # 검색된 날짜 기준에 마지막 결제일이 포함되어 있는 DB의 리스트 (누적 결제건)
        paid_dblist = mlist.dbmkname.filter(db_lastpaiddate__range=[geton['set_date'][0], geton['set_date'][1]],
                                            db_paidstatus='Y')
        for dlist in paid_dblist:
            # 검색된 DB의 이번달 내지 검색된 날짜 기준으로 결제된 금액을 구함
            inner_paid_list = dlist.plchkdb.filter(pl_paiddate__range=[geton['set_date'][0], geton['set_date'][1]])
            for pilist in inner_paid_list:
                paid_a_sum = paid_a_sum + pilist.pl_paidprice

        # 누적 결제금
        all_count = all_dblist.count()
        paid_count = paid_dblist.count()
        mk_on_list[ii]['acc_count'] = len(paid_dblist)
        if paid_count > 0:
            mk_on_list[ii]['acc_per'] = "%.2f%%" % (paid_count / all_count * 100.0)
        else:
            mk_on_list[ii]['acc_per'] = '0%'
        mk_on_list[ii]['acc_price'] = paid_a_sum

        if paid_count > 0:
            acc_aver = paid_a_sum // paid_count
            mk_on_list[ii]['acc_aver'] = acc_aver
        else:
            mk_on_list[ii]['acc_aver'] = 0

        if not spend_db['dbn_price__sum']:
            mk_on_list[ii]['spend_db'] = 0
        else:
            mk_on_list[ii]['spend_db'] = spend_db['dbn_price__sum']

        ii += 1

    pagenum = make_get_page(mk_on_list, geton['get_page_num'], 10)
    mk_on_list = mk_on_list[pagenum[0]:pagenum[1]]

    return render(request, 'dbmanageapp/marketer_stats.html',
                  {'mk_on_list': mk_on_list, 'get_list': geton, 'pageval': pagenum[4],
                   'get_page_num': geton['get_page_num'], 'marketing_list': marketing_list})


@login_required
def alldblist(request):
    # 상태값 입력 안되었을때 에러처리
    try:
        chk_db = DbSetting.objects.last()
        all_status = chk_db.ds_status
        status_list = all_status.split(',')
        if not all_status:
            raise Http404()
    except:
        error = "상태값을 먼저 셋팅 해주세요"
        return render(request, 'dbmanageapp/alldblist.html', {'error': error})

    # 마케팅 리스트 에러 처리 (초기값 셋팅 X)
    try:
        marketing_list = MarketingList.objects.all()
    except:
        error = '마케팅 리스트를 추가해주세요!'
        return render(request, 'dbmanageapp/alldblist.html', {'error': error})

    # 담당자(매니저) 리스트 뿌려주기
    manager_list = User.objects.filter(rete='D')

    # 여기서부터 Q값 넣기 시작!!
    q = Q()
    j = Q()

    get_list = {}
    geton = get_getlist(request, q, j)
    print(geton)
    status_count = []

    for slist in status_list:
        status_get = UploadDb.objects.select_related('db_mkname').filter(q).filter(db_status=slist)
        status_count.append(status_get.count())

    q.add(Q(db_date__range=[geton['set_date'][0], geton['set_date'][1]]), q.AND)
    # 전체 페이지값을 구해 페이지네이션을 구현한 뒤 원하는 갯수만큼 출력
    db_list = UploadDb.objects.select_related('db_mkname').filter(q)
    pagenum = make_get_page(db_list, geton['get_page_num'], geton['wp'])
    db_list_val = UploadDb.objects.select_related('db_mkname').filter(q).order_by('-id')[pagenum[0]:pagenum[1]]

    if request.method == 'POST':
        list_num = request.POST.getlist('listcount[]')
        list_id = request.POST.getlist('listid[]')
        change_status = request.POST.getlist('change_status[]')
        change_manager = request.POST['change_manager']
        change_manager_nick = request.POST['change_manager_nick']

        for val in list_num:
            temp_item = UploadDb.objects.get(id=list_id[int(val)])
            temp_item.db_status = change_status[int(val)]
            if change_manager:
                temp_item.db_manager = change_manager
                temp_item.db_manager_nick = change_manager_nick
            temp_item.save()

    print(get_list)

    return render(request, 'dbmanageapp/alldblist.html',
                  {'db_list_val': db_list_val, 'manager_list': manager_list, 'all_status': all_status,
                   'status_list': status_list, 'status_count': status_count,
                   'marketing_list': marketing_list, 'pageval': pagenum[4],
                   'get_page_num': geton['get_page_num'], 'get_list': geton}, )


@login_required
def emp_dblist(request):
    # 여기서부터 Q값 넣기 시작!!
    q = Q()
    j = Q()
    get_list = {}
    geton = get_getlist(request, q, j)
    status_count = []

    try:
        chk_db = DbSetting.objects.last()
        all_status = chk_db.ds_status
        status_list = all_status.split(',')
        if not all_status:
            raise Http404()
    except:
        error = "상태값을 먼저 셋팅 해주세요"
        return render(request, 'dbmanageapp/alldblist.html', {'error': error})


    status_count = []
    for slist in status_list:
        status_get = UploadDb.objects.select_related('db_mkname').filter(q).filter(db_status=slist)
        status_count.append(status_get.count())

    q.add(Q(db_date__range=[geton['set_date'][0], geton['set_date'][1]]), q.AND)
    q.add(Q(db_manager=request.user), q.AND)
    # 전체 페이지값을 구해 페이지네이션을 구현한 뒤 원하는 갯수만큼 출력
    db_list = UploadDb.objects.select_related('db_mkname').filter(q)
    pagenum = make_get_page(db_list, geton['get_page_num'], geton['wp'])
    db_list_val = UploadDb.objects.select_related('db_mkname').filter(q).order_by('-id')[pagenum[0]:pagenum[1]]

    if request.method == 'POST':
        list_num = request.POST.getlist('listcount[]')
        list_id = request.POST.getlist('listid[]')
        change_status = request.POST.getlist('change_status[]')
        change_manager = request.POST['change_manager']
        change_manager_nick = request.POST['change_manager_nick']

        for val in list_num:
            temp_item = UploadDb.objects.get(id=list_id[int(val)])
            temp_item.db_status = change_status[int(val)]
            if change_manager:
                temp_item.db_manager = change_manager
                temp_item.db_manager_nick = change_manager_nick
            temp_item.save()

    print(get_list)
    return render(request, 'dbmanageapp/emp_dblist.html',
                  {'db_list_val': db_list_val, 'status_count': status_count, 'status_count': status_count,
                   'status_list': status_list,
                   'pageval': pagenum[4], 'get_page_num': geton['get_page_num'], 'get_list': geton}, )


@login_required
def emp_dbstats(request):
    print(request.user)
    # -------------- 뿌려주기 옵션값 끝!
    q = Q()
    j = Q()

    get_list = {}
    geton = get_getlist(request, q, j)
    print(geton)

    q.add(Q(db_manager=request.user), q.AND)
    j.add(Q(db_manager=request.user), q.AND)

    q.add(Q(db_date__range=[geton['set_date'][0], geton['set_date'][1]]), q.AND)
    j.add(Q(db_date__range=[geton['set_date'][0], geton['set_date'][1]]), q.AND)

    q.add(Q(db_paidstatus='Y'), q.AND)
    q.add(~Q(db_manager=''), q.AND)

    db_list = UploadDb.objects.select_related('db_mkname').filter(q)
    pagenum = make_get_page(db_list, geton['get_page_num'], geton['wp'])
    base_db = UploadDb.objects.select_related('db_mkname').filter(q).order_by('-id')[pagenum[0]:pagenum[1]]

    sum = UploadDb.objects.filter(q).aggregate(Sum('db_paidprice'))
    if not sum['db_paidprice__sum']:
        sum['db_paidprice__sum'] = 0

    return render(request, 'dbmanageapp/emp_dbstats.html',
                  {'base_db': base_db, 'pageval': pagenum[4],
                   'get_page_num': geton['get_page_num'], 'get_list': geton, 'sum': sum})


@login_required
def sale_st(request):
    ## 기본 선택값 뿌려주기
    # 담당자(매니저) 리스트 뿌려주기
    manager_list = User.objects.filter(rete='D')

    # -------------- 뿌려주기 옵션값 끝!
    q = Q()
    j = Q()

    get_list = {}
    geton = get_getlist(request, q, j)

    q.add(Q(db_date__range=[geton['set_date'][0], geton['set_date'][1]]), q.AND)
    j.add(Q(db_date__range=[geton['set_date'][0], geton['set_date'][1]]), q.AND)

    q.add(Q(db_paidstatus='Y'), q.AND)
    q.add(~Q(db_manager=''), q.AND)

    db_list = UploadDb.objects.select_related('db_mkname').filter(q)
    pagenum = make_get_page(db_list, geton['get_page_num'], geton['wp'])
    base_db = UploadDb.objects.select_related('db_mkname').filter(q).order_by('-id')[pagenum[0]:pagenum[1]]

    sum = UploadDb.objects.filter(q).aggregate(Sum('db_paidprice'))
    if not sum['db_paidprice__sum']:
        sum['db_paidprice__sum'] = 0

    return render(request, 'dbmanageapp/sale_st.html',
                  {'base_db': base_db, 'pageval': pagenum[4],
                   'get_page_num': geton['get_page_num'], 'manager_list': manager_list,
                   'get_list': geton, 'sum': sum})


@login_required
def divdb(request):
    # 마케팅 리스트 에러 처리 (초기값 셋팅 X) + 값 뿌려주기
    try:
        marketing_list = MarketingList.objects.all()
    except:
        error = '마케팅 리스트를 추가해주세요!'
        return render(request, 'dbmanageapp/alldblist.html', {'error': error})
    q = Q()
    # 미분배 DB 목록 수량 구하기
    db_count_arr = []
    dbn_list = UploadDbName.objects.all()
    for dnlist in dbn_list:

        arr = []
        q.add(Q(db_manager__isnull=True), q.AND)
        q.add(Q(db_name=dnlist), q.AND)
        db_count = UploadDb.objects.filter(q).count()
        if (db_count > 0):
            arr.append(dnlist.dbn_mkname.mk_company)
            arr.append(dnlist.dbn_name)
            arr.append(db_count)
            arr.append(dnlist.dbn_date)
            db_count_arr.append(arr)

    # 검색 조건들 받자
    j = Q()
    j.add(Q(db_manager__isnull=True), j.AND)

    geton = get_getlist(request, q, j)
    # 날짜 GET 값 받기 에러 처리

    db_list = UploadDb.objects.filter(j)
    userlist = User.objects.filter(rete='D')

    error_text = ""

    if request.method == 'POST':
        divdb_list = request.POST.getlist('divdb[]')
        divnick_list = request.POST.getlist('divnick[]')
        divid_list = request.POST.getlist('divid[]')

        list_int = listStrToInt(divdb_list)
        sum_listint = sum(list_int)

        try:
            if sum_listint == 0 or sum_listint > db_list.count():
                raise
            k = 0
            for list in list_int:
                db_list = UploadDb.objects.filter(db_manager__isnull=True)
                db_id_list = []
                for onid in db_list:
                    db_id_list.append(onid.id)

                random_val = random.sample(db_id_list, list)
                for i in random_val:
                    div_dv_update = UploadDb.objects.get(id=i)
                    div_dv_update.db_manager = divid_list[k]
                    div_dv_update.db_manager_nick = divnick_list[k]
                    div_dv_update.save()
                k += 1
            return HttpResponseRedirect(reverse('dbmanage:divdb'))
        except:
            print('여기는 안오는거야??')
            divdb_list = request.POST.getlist('divdb[]')
            list_int = listStrToInt(divdb_list)
            if sum(list_int) == 0:
                error_text = '분배할 값이 입력되지 않았습니다.'
            elif sum(list_int) > db_list.count():
                error_text = '분배할 값이 DB 수량보다 많습니다.'

    return render(request, 'dbmanageapp/divdb.html',
                  {'db_list': db_list, 'userlist': userlist, 'db_count_arr': db_count_arr, 'get_list': geton,
                   'marketing_list': marketing_list, 'error_text': error_text})


@login_required
def markerlist(request):
    if request.method == 'POST':
        btnval = request.POST['gosubmit']
        print(btnval)
        if btnval == 'create':
            newmarketer = MarketingList(mk_company=request.POST['mk_company'], mk_name=request.POST['mk_name'],
                                        mk_phone=request.POST['mk_phone'], mk_advtype=request.POST['mk_advtype'],
                                        mk_url=request.POST['mk_url'], mk_memo=request.POST['mk_memo'])
            newmarketer.save()
        elif btnval == 'update':
            mk_id = request.POST['mk_id']
            updatemarketer = MarketingList.objects.get(id=mk_id)
            updatemarketer.mk_company = request.POST['mk_company']
            updatemarketer.mk_name = request.POST['mk_name']
            updatemarketer.mk_phone = request.POST['mk_phone']
            updatemarketer.mk_advtype = request.POST['mk_advtype']
            updatemarketer.mk_url = request.POST['mk_url']
            updatemarketer.mk_status = request.POST['mk_status']
            updatemarketer.save()
        else:
            mk_id = request.POST['mk_id']
            updatemarketer = MarketingList.objects.get(id=mk_id)
            updatemarketer.delete()

    marketing_list = MarketingList.objects.all()
    return render(request, 'dbmanageapp/marketinglist.html', {'marketing_list': marketing_list})


@login_required
def newdbup(request):
    if request.method == 'POST':

        dblist_text = request.POST['dblist_text']
        if dblist_text and request.FILES.get('dblist_file') is None:
            dblist_text = dblist_text.splitlines(False)

            i = 0
            dblist = []
            for val in dblist_text:
                val = re.sub("\!|\'|\?|\-", "", val)
                val = val.split(',')
                if val[0].isdigit():
                    val[0] = val[0].zfill(11)
                if len(val) == 1:
                    val.append(val[0])
                dblist.append(val)
        else:
            if request.FILES.get('dblist_file') is not None:
                files = request.FILES.get('dblist_file')
                load_wb = load_workbook(files, data_only=True)
                load_ws = load_wb['Sheet1']
                dblist = []
                for row in load_ws.rows:
                    row_value = []
                    cellval = ""
                    for cell in row:
                        cellval = cell.value

                        cellval = str(cellval)
                        cellval = re.sub("\!|\'|\?|\-", "", cellval)
                        if cellval.isdigit():
                            cellval = cellval.zfill(11)
                        if cellval == 'None' or not cellval:
                            cellval = temp_cellval
                        row_value.append(cellval)
                        temp_cellval = cellval

                    dblist.append(row_value)

        if dblist:
            dbn_mkname = request.POST.get('dbn_mkname')
            dbn_name = request.POST.get('dbn_name')
            dbn_price = request.POST.get('dbn_price')
            dbn_price = re.sub("\!|\'|\,|\-", "", dbn_price)
            dbn_price = int(dbn_price)
            dbn_memo = request.POST.get('dbn_memo')
            chk_ml = MarketingList.objects.get(mk_company=dbn_mkname)
            dbn_items = UploadDbName(dbn_mkname=chk_ml, dbn_name=dbn_name, dbn_price=dbn_price, dbn_memo=dbn_memo)
            dbn_items.save()

            temp_udb = UploadDbName.objects.last()
            onfr = UploadDbName.objects.get(id=temp_udb.id)
            temp_mkt = MarketingList.objects.get(mk_company=dbn_mkname)
            for dbval in dblist:
                # DB에 값 넣기
                if len(dbval) < 5:
                    set_arr_count = 5 - len(dbval)
                    print(set_arr_count)
                    for i in range(set_arr_count):
                        dbval.append('')
                print(dbval)
                excelup = UploadDb(db_name=onfr, db_mkname=temp_mkt, db_member=dbval[1], db_phone=dbval[0],
                                   db_age=dbval[2], db_sex=dbval[3], db_inv=dbval[4])
                excelup.save()

            messages.success(request, 'DB 업로드가 완료 되었습니다.')
        else:

            error = "업로드 요청된 DB가 없습니다. DB를 입력해주세요"
            return HttpResponseRedirect(reverse('dbmanage:newdbup'))

    try:
        marketing_list = MarketingList.objects.all()
    except:
        marketing_list = '마케팅 리스트를 추가해주세요!'

    try:
        sample_list = AllManage.objects.last()
        print(sample_list)
        print(sample_list.sample_excel_file.path)
    except:
        sample_list = ""

    return render(request, 'dbmanageapp/newdbup.html', {'marketing_list': marketing_list, 'sample_list': sample_list})


# **********************************


def accountmanagement(request):
    if request.method == 'POST':
        id_list = request.POST.getlist('idlist[]')
        id_count = request.POST.getlist('idcount[]')
        manager_status = request.POST.getlist('manager_status[]')
        manager_rate = request.POST.getlist('manager_rate[]')

        i = 0
        for val in id_count:
            temp_user = User.objects.get(id=id_list[int(val)])
            print(temp_user)
            temp_user.rete = manager_rate[int(val)]
            temp_user.status = manager_status[int(val)]
            temp_user.save()

            i += 1

    user_list = User.objects.all().order_by('-id')

    return render(request, 'dbmanageapp/accountmanagement.html', {'user_list': user_list})


def detail_customer(request, id):
    try:
        # 상태값 뿌려주기
        chk_db = DbSetting.objects.values_list()
        status_list = chk_db[0][1].split(',')
        # 회원정보 뿌려주기
        customer_info = UploadDb.objects.get(id=id)
        # 댓글 리스트 뿌려주기

        memo_list = DbMemo.objects.select_related('dm_chkdb').filter(dm_chkdb=customer_info).order_by('-id')
    except:
        print('문제야 문제')
    db_status = UploadDb.objects.get(id=id)
    if request.method == 'POST':

        if request.POST['sbm_button'] == 'update':
            status_sel = request.POST['status_sel']
            payment_sel = request.POST['paystatus_sel']

            db_status.db_status = status_sel
            db_status.db_paidstatus = payment_sel
            db_status.save()

            messages.success(request, '정상적으로 업데이트 되었습니다.')
            return HttpResponseRedirect(reverse('dbmanage:detail_customer', kwargs={'id': id}))
        elif request.POST['sbm_button'] == 'payment':

            payment_val = request.POST['db_payment']
            payment_val = re.sub(",", "", payment_val)
            payment_val = int(payment_val)

            paidlist = PaidList()
            paidlist.pl_paidprice = payment_val
            paidlist.pl_chkdb = db_status
            paidlist.save()

            db_status.db_paidstatus = 'Y'
            set_paidstatus = DbSetting.objects.last()

            db_status.db_status = set_paidstatus.ds_statusbase
            sum = db_status.plchkdb.aggregate(Sum('pl_paidprice'))
            db_status.db_paidprice = sum['pl_paidprice__sum']
            temp_now_date = timezone.now()
            db_status.db_lastpaiddate = temp_now_date
            db_status.save()
            messages.success(request, '결제값이 업데이트 되었습니다.')
            return HttpResponseRedirect(reverse('dbmanage:detail_customer', kwargs={'id': id}))

    basedb_paidlist = db_status.plchkdb.all()

    sum = db_status.plchkdb.aggregate(Sum('pl_paidprice'))

    return render(request, 'dbmanageapp/detail_customer.html',
                  {'customer_info': customer_info, 'status_list': status_list, 'memo_list': memo_list,
                   'basedb_paidlist': basedb_paidlist, 'sum': sum})


def workAjax(request):
    jsonObject = json.loads(request.body)
    if 'status_list' in jsonObject:
        bring_status = jsonObject.get('status_list')
        set_db = DbSetting.objects.all()
        if set_db.count() == 0:
            setting_status = DbSetting(ds_status=bring_status)
            setting_status.save()
        else:
            chk_db = DbSetting.objects.values_list()
            setdb_key = chk_db[0][0]
            update_set_status = DbSetting.objects.get(id=setdb_key)
            update_set_status.ds_status = bring_status
            update_set_status.save()

    elif 'db_memo' in jsonObject:
        bring_memo = jsonObject.get('db_memo')
        bring_id = jsonObject.get('now_id')
        chk_uploadub = UploadDb.objects.get(id=bring_id)
        set_dbmemo = DbMemo(dm_chkdb=chk_uploadub, dm_memos=bring_memo)
        set_dbmemo.save()

    elif 'mk_name' in jsonObject:
        bring_mkname = jsonObject.get('mk_name')
        bring_sd = jsonObject.get('date_sd')
        bring_sd = datetime.strptime(bring_sd, '%Y-%m-%d')
        bring_ed = jsonObject.get('date_ed')
        bring_ed = datetime.strptime(bring_ed, '%Y-%m-%d')
        set_date = set_search_day(bring_sd, bring_ed)

        mk_name = MarketingList.objects.get(mk_company=bring_mkname)

        chk_dbname = UploadDbName.objects.filter(dbn_mkname=mk_name, dbn_date__range=[set_date[0], set_date[1]])
        dbname_arr = []
        for dbname in chk_dbname:
            dbname_arr.append(dbname.dbn_name)

        jsonObject = {'db_names': dbname_arr}
    elif 'del_val' in jsonObject:
        detail_id = jsonObject.get('detail_id')
        PaidList.objects.get(id=detail_id).delete()

    elif 'change_price' in jsonObject:
        detail_id = jsonObject.get('detail_id')
        change_price = jsonObject.get('change_price')
        update_item = PaidList.objects.get(id=detail_id)
        update_item.pl_paidprice = change_price
        print(update_item.pl_chkdb)
        update_item.save()

    elif 'add_username' in jsonObject:
        add_username = jsonObject.get('add_username')
        add_nickname = jsonObject.get('add_nickname')
        add_password = jsonObject.get('add_password')

        try:
            User.objects.create_user(username=add_username, password=add_password, nickname=add_nickname, )
            context = {'success_msg': '정상적으로 가입 되었습니다.'}
            return JsonResponse(context)
        except:
            return {'error!!'}
    elif 'change_pw_input' in jsonObject:
        context = {'chdii': '비밀번호 변경!!'}

        receive_num = jsonObject.get('choices_num')
        receive_pwd = jsonObject.get('change_pw_input')
        print(type(receive_num))
        user = User.objects.get(id=int(receive_num))
        user.set_password(receive_pwd)
        user.save()
        return JsonResponse(context)
    else:
        print('-------------------')
        # Http404()
        context = {'testpppp': 'testkjkasjdfkajsdkfj'}
        return JsonResponse(context)

    return JsonResponse(jsonObject)


def test_chk(requese):
    # testitem = UploadDb.objects.select_related('db_name').get(id=869)
    # print(testitem.db_name.dbn_name)
    #
    # testitem = UploadDb.objects.get(id=869)
    # print(testitem.db_name.dbn_name)

    # chk_mk = MarketingList.objects.get(id=6)
    # print(chk_mk.mk_company)

    test1 = MarketingList.objects.get(id=5)
    test1['testval'] = 'asdjflkasjdjsdf'
    print(test1.testval)
    # test2 = test1.mkdname.get(id=35)
    # test3 = test2.dbname.all()
    # print(test3)
    #
    # test4 = MarketingList.objects.all()
    # for list in test4:
    #     for inlist in list.mkdname.all():
    #         inlist.dbname.all()

    # # test_chk = DbMemo.objects.select_related('dm_chkdb').filter(dm_chkdb=insi)
    # for list in insi:
    #     print(list.testfield.all())

    return render(requese, 'dbmanageapp/test_chk.html', )


# ************** custom 함수

def get_getlist(request, q, j):
    get_list = {}

    # 현재 상태 받기 에러처리!!
    try:
        ps = request.GET['ps']
        get_list['ps'] = ps
        if ps:
            q.add(Q(db_phone__icontains=ps), q.AND)

    except:
        get_list['ps'] = ''

    # DB 이름 받기 에러처리!!
    try:
        dn = request.GET['dn']
        get_list['dn'] = dn
        temp_dbnname = UploadDbName.objects.get(dbn_name=dn)
        q.add(Q(db_name=temp_dbnname), q.AND)
        j.add(Q(db_name=temp_dbnname), q.AND)
    except:
        get_list['dn'] = ''

    # 담당자 (매니저) 받기 에러처리!
    try:
        ns = request.GET['ns']
        get_list['ns'] = ns
        if ns:
            q.add(Q(db_status=ns), q.AND)
    except:
        get_list['ns'] = ''

    # 담당자 (매니저) 받기 에러처리!
    try:
        mn = request.GET['mn']
        get_list['mn'] = mn
        if mn:
            q.add(Q(db_manager=mn), q.AND)
    except:
        get_list['mn'] = ''

    # 페이지 개수 받기 에러처리
    try:
        wp = request.GET['wp']
        wp = int(wp)
    except:
        wp = 10
    get_list['wp'] = wp

    # 마케터 받기 에러처리
    try:
        mk = request.GET['mk']
        if mk:
            get_list['mk'] = mk
            chk_ml = MarketingList.objects.get(mk_company=mk)
            q.add(Q(db_mkname=chk_ml), q.AND)
    except:
        print('이상 없음!!')

    # 현재 페이지 값 받기 에러처리
    try:
        get_page_num = request.GET['page']
        get_page_num = int(get_page_num)
    except:
        get_page_num = 1

    get_list['get_page_num'] = get_page_num

    # 날짜 받기 에러처리!
    try:
        sd = request.GET['sd']
        get_list['sd'] = sd
        sd = datetime.strptime(sd, '%Y-%m-%d')
        ed = request.GET['ed']
        get_list['ed'] = ed
        ed = datetime.strptime(ed, '%Y-%m-%d')
        set_date = set_search_day(sd, ed)
    except:
        print('날짜 못받니??')
        now_datetime = datetime.today()
        f_datetime = datetime(now_datetime.year, now_datetime.month, 1)
        set_date = set_search_day(f_datetime, now_datetime)
    get_list['set_date'] = set_date

    get_list['q'] = q
    return get_list


def make_get_page(alllist, get_page_num, wantpage):
    # param1 : 전체 게시물 갯수 / param2 : 현재 페이지
    # 전체 카운트를 구해 원하는 숫자로 쪼개 페이지를 나눈다.
    pagecount = divmod(len(alllist), wantpage)
    temp_count = 0
    pagelist = []
    while temp_count <= pagecount[0]:
        temp_count = temp_count + 1
        pagelist.append(temp_count)

    get_page_num = int(get_page_num)
    startpage = (get_page_num - 1) * wantpage
    searchpage = get_page_num * wantpage

    get_last_page_num = int(pagecount[0])
    get_last_page_num = get_last_page_num + 1

    start_page_num = int(get_page_num) - 3
    end_page_num = int(get_page_num) + 2

    if start_page_num <= 0:
        pageval = pagelist[0:5]
    elif end_page_num >= get_last_page_num:
        fullpageval = get_last_page_num
        startval = fullpageval - 5
        pageval = pagelist[startval:fullpageval]
    else:
        pageval = pagelist[start_page_num:end_page_num]
    # 페이지 시작 값 / 몇개 노출할건지? / 전체 페이지 리스트 / 뭐더라?? 안씀 / 필터링 된 페이지 리스트
    return [startpage, searchpage, pagelist, pagecount, pageval]


def set_search_day(start_time, end_time):
    start_of_datetime = start_time.replace(hour=0, minute=0, second=0, microsecond=000000)

    end_of_day_datetime = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
    result = [start_of_datetime, end_of_day_datetime]
    return result


def listStrToInt(list_str):
    i = 0
    for list in list_str:
        if list == '':
            del list_str[i]
            list_str.insert(i, '0')
        i += 1
    list_int = [int(i) for i in list_str]
    return list_int