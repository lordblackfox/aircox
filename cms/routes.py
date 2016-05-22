from django.conf.urls import url
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import ugettext as _, ugettext_lazy


class Route:
    """
    Base class for routing. Given a model, we generate url specific for each
    type of route.

    The generated url takes this form:
        name + '/' + route_name + '/' + '/'.join(route_url_args)

    And their name (to use for reverse:
        name + '_' + route_name

    By default name is the verbose name of the model. It is always in
    singular form.
    """
    name = None         # route name
    url_args = []       # arguments passed from the url [ (name : regex),... ]

    @classmethod
    def get_queryset(cl, website, model, request, **kwargs):
        """
        Called by the view to get the queryset when it is needed
        """
        pass

    @classmethod
    def get_object(cl, website, model, request, **kwargs):
        """
        Called by the view to get the object when it is needed
        """
        pass

    @classmethod
    def get_title(cl, model, request, **kwargs):
        return ''

    @classmethod
    def get_view_name(cl, name):
        return name + '_' + cl.name

    @classmethod
    def as_url(cl, name, view, view_kwargs = None):
        pattern = '^{}/{}'.format(name, cl.name)
        if cl.url_args:
            url_args = '/'.join([
                '(?P<{}>{}){}'.format(
                    arg, expr,
                    (optional and optional[0] and '?') or ''
                )
                for arg, expr, *optional in cl.url_args
            ])
            pattern += '/' + url_args
        pattern += '/?$'

        kwargs = {
            'route': cl,
        }
        if view_kwargs:
            kwargs.update(view_kwargs)

        return url(pattern, view, kwargs = kwargs,
                   name = cl.get_view_name(name))


class DetailRoute(Route):
    name = 'detail'
    url_args = [
        ('pk', '[0-9]+'),
        ('slug', '(\w|-|_)+', True),
    ]

    @classmethod
    def get_object(cl, website, model, request, pk, **kwargs):
        return model.objects.get(pk = int(pk))


class AllRoute(Route):
    name = 'all'

    @classmethod
    def get_queryset(cl, website, model, request, **kwargs):
        return model.objects.all()

    @classmethod
    def get_title(cl, model, request, **kwargs):
        return _('All %(model)s') % {
            'model': model._meta.verbose_name_plural
        }


class ThreadRoute(Route):
    """
    Select posts using by their assigned thread.

    - "thread_model" can be a string with the name of a registered item on
    website or a model.
    - "pk" is the pk of the thread item.
    """
    name = 'thread'
    url_args = [
        ('thread_model', '(\w|_|-)+'),
        ('pk', '[0-9]+'),
    ]

    @classmethod
    def get_queryset(cl, website, model, request, thread_model, pk, **kwargs):
        if type(thread_model) is str:
            thread_model = website.registry.get(thread_model)

        if not thread_model:
            return

        thread_model = ContentType.objects.get_for_model(thread_model)
        return model.objects.filter(
            thread_type = thread_model,
            thread_pk = int(pk)
        )


class DateRoute(Route):
    name = 'date'
    url_args = [
        ('year', '[0-9]{4}'),
        ('month', '[0-9]{2}'),
        ('day', '[0-9]{1,2}'),
    ]

    @classmethod
    def get_queryset(cl, website, model, request, year, month, day, **kwargs):
        return model.objects.filter(
            date__year = int(year),
            date__month = int(month),
            date__day = int(day),
        )


class SearchRoute(Route):
    name = 'search'

    @classmethod
    def get_queryset(cl, website, model, request, q, **kwargs):
        qs = model.objects
        for search_field in model.search_fields or []:
            r = model.objects.filter(**{ search_field + '__icontains': q })
            if qs: qs = qs | r
            else: qs = r

        qs.distinct()
        return qs

## TODO: by tag

