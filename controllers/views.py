import json

from django.views.generic.base import View, TemplateResponseMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _, ugettext_lazy
from django.utils import timezone as tz

import aircox.controllers.models as models


class Stations:
    stations = models.Station.objects.all()
    update_timeout = None
    fetch_timeout = None

    def fetch(self):
        if self.fetch_timeout and self.fetch_timeout > tz.now():
            return

        self.fetch_timeout = tz.now() + tz.timedelta(seconds = 5)
        for station in self.stations:
            station.prepare(fetch = True)


stations = Stations()


def on_air(request):
    try:
        import aircox.cms.models as cms
    except:
        cms = None

    station = request.GET.get('station');
    if station:
        station = stations.stations.filter(name = station)
    else:
        station = stations.stations.first()

    last = station.on_air(count = 1)
    if not last:
        return HttpResponse('')

    last = last[0]
    if type(last) == models.Log:
        last = {
            'type': 'track',
            'artist': last.related.artist,
            'title': last.related.title,
            'date': last.date,
        }
    else:
        try:
            publication = None
            if cms:
                publication = \
                    cms.DiffusionPage.objects.filter(
                        diffusion = last.initial or last).first() or \
                    cms.ProgramPage.objects.filter(
                        program = last.program).first()
        except:
            pass

        last = {
            'type': 'diffusion',
            'title': publication.title if publication else last.program.name,
            'date': last.start,
            'url': publication.specific.url if publication else None,
        }

    last['date'] = str(last['date'])
    return HttpResponse(json.dumps(last))




class Monitor(View,TemplateResponseMixin):
    template_name = 'aircox/controllers/monitor.html'

    def get_context_data(self, **kwargs):
        stations.fetch()
        return { 'stations': stations.stations }

    def get (self, request = None, **kwargs):
        self.request = request
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)

    def post (self, request = None, **kwargs):
        if not 'action' in request.POST:
            return HttpResponse('')

        POST = request.POST
        controller = POST.get('controller')
        action = POST.get('action')

        station = stations.stations.filter(name = POST.get('station')) \
                                   .first()
        if not station:
            return HttpResponse('')
        station.prepare(fetch=True)

        if station and action == 'skip':
            station.controller.skip()

        return HttpResponse('')



