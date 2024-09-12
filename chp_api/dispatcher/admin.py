from django.contrib import admin

from .models import App, ZenodoFile, DispatcherSetting

admin.site.register(App)
admin.site.register(ZenodoFile)
admin.site.register(DispatcherSetting)
