from django.contrib import admin

# Register your models here.
from dbmanageapp.models import MarketingList, UploadDbName, UploadDb, DbSetting, DbMemo, TestField, PaidList

admin.site.register(MarketingList)

admin.site.register(UploadDbName)

admin.site.register(UploadDb)

admin.site.register(DbSetting)

admin.site.register(DbMemo)

admin.site.register(TestField)

admin.site.register(PaidList)
