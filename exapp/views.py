import xlwt
from django.http import HttpResponse
from django.shortcuts import render


# Create your views here.
from dbmanageapp.models import UploadDb


def exdown(request):

    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment;filename*=UTF-8\'\'example.xls'
    wb = xlwt.Workbook(encoding='ansi')  # encoding은 ansi로 해준다.
    ws = wb.add_sheet('sheet1')  # 시트 추가

    row_num = 0
    col_names = ['db_phone', 'db_member']
    for idx, col_name in enumerate(col_names):
        ws.write(row_num, idx, col_name)

    rows = UploadDb.objects.all().values_list('db_phone','db_member')
    print(rows)
    for row in rows:
        row_num += 1
        for col_num, attr in enumerate(row):
            ws.write(row_num, col_num, attr)

    wb.save(response)
    print(response)
    # print(set_db)
    return response

def ex_setting(request):
    response = HttpResponse(content_type="application/vnd.ms-excel")
    response["Content-Disposition"] = 'attachment;filename*=UTF-8\'\'example.xls'
    wb = xlwt.Workbook(encoding='ansi')  # encoding은 ansi로 해준다.
    ws = wb.add_sheet('sheet1')  # 시트 추가

    row_num = 0
    col_names = ['db_phone', 'db_member']
    for idx, col_name in enumerate(col_names):
        ws.write(row_num, idx, col_name)

    rows = UploadDb.objects.all().values_list('db_phone', 'db_member')
    print(rows)
    for row in rows:
        print(row)
        row_num += 1
    return render(request, 'exapp/ex_seton.html')

