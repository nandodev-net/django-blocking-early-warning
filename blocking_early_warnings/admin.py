from django.contrib import admin
from .models import *


class UrlListAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "parse_strategy", "storage_type")


class UrlAdmin(admin.ModelAdmin):
    list_display = ["url"]


class AsnAdmin(admin.ModelAdmin):
    list_display = ("name", "code")


admin.site.register(UrlList, UrlListAdmin)
admin.site.register(Url, UrlAdmin)
admin.site.register(ASN, AsnAdmin)
