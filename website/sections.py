import json

from django.utils import timezone as tz
from django.utils.translation import ugettext as _, ugettext_lazy

import aircox.programs.models as programs
import aircox.cms.models as cms
import aircox.cms.routes as routes
import aircox.cms.sections as sections
import aircox.cms.decorators as decorators

import aircox.website.models as models


@decorators.parts
class Player(sections.Section):
    """
    Display a player that is cool.
    """
    template_name = 'aircox/website/player.html'
    live_streams = []
    """
    A ListItem objects that display a list of available streams.
    """
    #default_sounds

    @decorators.part
    @decorators.template(template_name = 'aircox/cms/list_item.html')
    def on_air(cl, request):
        """
        View that return what is on air formatted in JSON.
        """
        qs = programs.Diffusion.get(
            now = True,
            type = programs.Diffusion.Type.normal
        )

        if not qs or not qs[0].is_date_in_my_range():
            return ''

        qs = qs[0]
        post = models.Diffusion.objects.filter(related = qs)
        if not post:
            post = models.Program.objects.filter(related = qs.program)

        if not post:
            post = ListItem(title = qs.program.name)
        else:
            post = post[0]

        return {
            'item': post,
            'list': sections.List,
        }

        return json.dumps({ 'title': post.title, 'url': post.url() })

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({
            'base_template': 'aircox/cms/section.html',
            'live_streams': self.live_streams,
            'last_sounds': models.Sound.objects. \
                                filter(published = True). \
                                order_by('-pk')[:10],
        })
        return context


class Diffusions(sections.List):
    """
    Section that print diffusions. When rendering, if there is no post yet
    associated, use the programs' article.
    """
    order_by = '-start'
    show_schedule = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_diffs(self, **filter_args):
        qs = programs.Diffusion.objects.filter(
            type = programs.Diffusion.Type.normal
        )
        if self.object:
            object = self.object.related
            if type(object) == programs.Program:
                qs = qs.filter(program = object)
            elif type(object) == programs.Diffusion:
                if object.initial:
                    object = object.initial
                qs = qs.filter(initial = object) | qs.filter(pk = object.pk)
        if filter_args:
            qs = qs.filter(**filter_args).order_by('start')

        return qs

        #r = []
        #if self.next_count:
        #    r += list(programs.Diffusion.get(next=True, queryset = qs)
        #                .order_by('-start')[:self.next_count])
        #if self.prev_count:
        #    r += list(programs.Diffusion.get(prev=True, queryset = qs)
        #                .order_by('-start')[:self.prev_count])
        #return r

    def get_object_list(self):
        diffs = self.get_diffs()

        posts = models.Diffusion.objects.filter(related__in = diffs)
        r = []
        for diff in diffs:
            diff_ = diff.initial if diff.initial else diff
            post = next((x for x in posts if x.related == diff_), None)
            if not post:
                post = sections.ListItem(date = diff.start)
            else:
                post = sections.ListItem(post=post)
                post.date = diff.start

            if diff.initial:
                post.info = _('rerun of %(day)s') % {
                    'day': diff.initial.start.strftime('%A %d/%m')
                }

            if self.object:
                post.update(self.object)
            else:
                thread = models.Program.objects. \
                            filter(related = diff.program, published = True)
                if thread:
                    post.update(thread[0])
            r.append(post)
        return [ sections.ListItem(post=post) for post in r ]

    @property
    def url(self):
        if not self.need_url():
            return

        if self.object:
            return models.Diffusion.route_url(routes.ThreadRoute,
                pk = self.object.id,
                thread_model = 'program',
            )
        return models.Diffusion.route_url(routes.AllRoute)

    @property
    def header(self):
        if not self.show_schedule:
            return None

        def str_sched(sched):
            info = ' <span class="info">(' + _('rerun of %(day)s') % {
                'day': sched.initial.date.strftime('%A')
            } + ')</span>' if sched.initial else ''

            text = _('%(day)s at %(time)s, %(freq)s') % {
                'day': sched.date.strftime('%A'),
                'time': sched.date.strftime('%H:%M'),
                'freq': sched.get_frequency_display(),
            }
            return text + info

        return ' / \n'.join([str_sched(sched)
                 for sched in programs.Schedule.objects \
                    .filter(program = self.object.related.pk)
        ])


class Playlist(sections.List):
    title = _('Playlist')
    message_empty = ''

    def get_object_list(self):
        tracks = programs.Track.objects \
                     .filter(diffusion = self.object.related) \
                     .order_by('position')
        return [ sections.ListItem(title=track.name, content=track.artist)
                    for track in tracks ]


class Sounds(sections.List):
    pass


class Schedule(Diffusions):
    """
    Render a list of diffusions in the form of a schedule
    """
    template_name = 'aircox/website/schedule.html'
    date = None
    nav_date_format = '%a. %d'
    fields = [ 'time', 'image', 'title']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_css_class('schedule')

    @staticmethod
    def get_week_dates(date):
        """
        Return a list of dates of the week of the given date.
        """
        first = date - tz.timedelta(days=date.weekday())
        return [ first + tz.timedelta(days=i) for i in range(0, 7) ]

    def date_or_default(self):
        if self.date:
            return self.date
        elif self.kwargs and 'year' in self.kwargs:
            return tz.datetime(year = int(self.kwargs['year']),
                               month = int(self.kwargs['month']),
                               day = int(self.kwargs['day']),
                               hour = 0, minute = 0, second = 0,
                               microsecond = 0)
        return tz.datetime.now()

    def get_object_list(self):
        date = self.date_or_default()
        qs = routes.DateRoute.get_queryset(
            models.Diffusion, self.request,
            year = date.year,
            month = date.month,
            day = date.day
        ).order_by('date')
        return qs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        date = self.date_or_default()
        dates = [
            (date, models.Diffusion.route_url(
                routes.DateRoute,
                year = date.year, month = date.month, day = date.day
            ))
            for date in self.get_week_dates(date)
        ]

        next_week = dates[-1][0] + tz.timedelta(days=1)
        next_week = models.Diffusion.route_url(
                routes.DateRoute,
                year = next_week.year, month = next_week.month,
                day = next_week.day
        )

        prev_week = dates[0][0] - tz.timedelta(days=1)
        prev_week = models.Diffusion.route_url(
                routes.DateRoute,
                year = prev_week.year, month = prev_week.month,
                day = prev_week.day
        )

        context.update({
            'date': date,
            'dates': dates,
            'next_week': next_week,
            'prev_week': prev_week,
        })
        return context

    @property
    def url(self):
        return None



#class DatesOfDiffusion(sections.List):
#    title = _('Dates of diffusion')
#
#    def get_object_list(self):
#        diffs = list(programs.Diffusion.objects. \
#            filter(initial = self.object.related). \
#            exclude(type = programs.Diffusion.Type.unconfirmed)
#        )
#        diffs.append(self.object.related)
#
#        items = []
#        for diff in sorted(diffs, key = lambda d: d.date, reverse = True):
#            info = ''
#            if diff.initial:
#                info = _('rerun')
#            if diff.type == programs.Diffusion.Type.canceled:
#                info += ' ' + _('canceled')
#            items.append(
#                sections.List.Item(None, diff.start.strftime('%c'), info, None,
#                                   'canceled')
#            )
#        return items
#
## TODO sounds
#
