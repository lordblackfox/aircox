from django.contrib import admin

import aircox.controllers.models as models


class SourceInline(admin.StackedInline):
    model = models.Source
    extra = 0

class OutputInline(admin.StackedInline):
    model = models.Output
    extra = 0


@admin.register(models.Station)
class StationAdmin(admin.ModelAdmin):
    inlines = [ SourceInline, OutputInline ]

@admin.register(models.Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'station', 'source', 'comment', 'related']
    list_filter = ['date', 'source', 'related_type']

admin.site.register(models.Source)
admin.site.register(models.Output)



