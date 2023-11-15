from django.contrib import admin

from .models import App, ZenodoFile, DispatcherSettings

admin.site.register(App)
admin.site.register(ZenodoFile)
admin.site.register(DispatcherSettings)
