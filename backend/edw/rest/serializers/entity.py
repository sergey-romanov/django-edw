# -*- coding: utf-8 -*-
from __future__ import unicode_literals


import types

from django.core import exceptions
from django.core.cache import cache
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.utils.six import with_metaclass
from django.utils.html import strip_spaces_between_tags
from django.utils.safestring import mark_safe, SafeText
from django.utils.translation import get_language_from_request

from rest_framework import serializers
from rest_framework.reverse import reverse

from edw import settings as edw_settings
from edw.models.entity import EntityModel
from edw.rest.serializers.data_mart import DataMartDetailSerializer


class AttributeSerializer(serializers.Serializer):
    """
    A serializer to convert the characteristics and marks for rendering.
    """
    name = serializers.CharField()
    path = serializers.CharField()
    values = serializers.ListField(child=serializers.CharField())
    view_class = serializers.ListField(child=serializers.CharField())


class EntityCommonSerializer(serializers.ModelSerializer):
    """
    Common serializer for the Entity model, both for the EntitySummarySerializer and the
    EntityDetailSerializer.
    """
    entity_model = serializers.CharField(read_only=True)

    class Meta:
        model = EntityModel
        extra_kwargs = {'url': {'view_name': 'edw:{}-detail'.format(model._meta.model_name)}}

    def render_html(self, entity, postfix):
        """
        Return a HTML snippet containing a rendered summary for this entity.
        Build a template search path with `postfix` distinction.
        """
        if not self.label:
            msg = "The Entity Serializer must be configured using a `label` field."
            raise exceptions.ImproperlyConfigured(msg)
        app_label = entity._meta.app_label.lower()
        request = self.context['request']
        cache_key = 'entity:{0}|{1}-{2}-{3}-{4}-{5}'.format(entity.id, app_label, self.label, entity.entity_model,
                                                            postfix, get_language_from_request(request))
        content = cache.get(cache_key)
        if content:
            return mark_safe(content)
        params = [
            (app_label.lower(), self.label.lower(), entity.entity_model.lower(), postfix),
            (app_label.lower(), self.label.lower(), 'entity', postfix),
            ('edw', self.label.lower(), 'entity', postfix),
        ]
        try:
            template = select_template(['{0}/entities/{1}-{2}-{3}.html'.format(*p) for p in params])
        except TemplateDoesNotExist:
            return SafeText("<!-- no such template: '{0}/entities/{1}-{2}-{3}.html' -->".format(*params[0]))
        # when rendering emails, we require an absolute URI, so that media can be accessed from
        # the mail client
        absolute_base_uri = request.build_absolute_uri('/').rstrip('/')
        context = {
            'entity': entity,
            'ABSOLUTE_BASE_URI': absolute_base_uri
        }
        content = strip_spaces_between_tags(template.render(context, request).strip())
        cache.set(cache_key, content, edw_settings.CACHE_DURATIONS['entity_html_snippet'])
        return mark_safe(content)


class SerializerRegistryMetaclass(serializers.SerializerMetaclass):
    """
    Keep a global reference onto the class implementing `EntitySummarySerializerBase`.
    There can be only one class instance, because the entities summary is the lowest common
    denominator for all entities of this edw instance. Otherwise we would be unable to mix
    different polymorphic entity types in the all list views.
    """
    def __new__(cls, clsname, bases, attrs):
        global entity_summary_serializer_class
        if entity_summary_serializer_class:
            msg = "Class `{}` inheriting from `EntitySummarySerializerBase` already registred."
            raise exceptions.ImproperlyConfigured(msg.format(entity_summary_serializer_class.__name__))
        new_class = super(cls, SerializerRegistryMetaclass).__new__(cls, clsname, bases, attrs)
        if clsname != 'EntitySummarySerializerBase':
            entity_summary_serializer_class = new_class
        return new_class

entity_summary_serializer_class = None


class EntitySummarySerializerBase(with_metaclass(SerializerRegistryMetaclass, EntityCommonSerializer)):
    """
    Serialize a summary of the polymorphic Entity model, suitable for Catalog List Views and other Views.
    """
    entity_url = serializers.SerializerMethodField()
    entity_type = serializers.CharField(read_only=True)

    short_characteristics = AttributeSerializer(read_only=True, many=True)
    short_marks = AttributeSerializer(read_only=True, many=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'summary')
        super(EntitySummarySerializerBase, self).__init__(*args, **kwargs)

    def get_entity_url(self, instance):
        request = self.context.get('request', None)
        format = self.context.get('format', None)
        return instance.get_absolute_url(request=request, format=format)


class RelatedDataMartSerializer(DataMartDetailSerializer):
    endpoint_url = serializers.SerializerMethodField()

    view_name = "edw:data-mart-entity-by-subject-list"

    class Meta(DataMartDetailSerializer.Meta):
        fields = ('endpoint_url',) + DataMartDetailSerializer.Meta.fields

    def get_endpoint_url(self, instance):

        request = self.context.get('request', None)
        kwargs = {
            'data_mart_pk': instance.id,
            'entity_pk': self.entity_pk,
        }
        format = self.context.get('format', None)
        return reverse(self.view_name, request=request, kwargs=kwargs, format=format)

    @property
    def entity_pk(self):
        return self.context.get('_entity_pk')


class EntityDetailSerializerBase(EntityCommonSerializer):
    """
    Serialize all fields of the Product model, for the products detail view.
    """
    characteristics = AttributeSerializer(read_only=True, many=True)
    marks = AttributeSerializer(read_only=True, many=True)
    related_data_marts = RelatedDataMartSerializer(many=True, read_only=True)

    _meta_cache = {}

    @staticmethod
    def _get_meta_class(base, model_class):

        class Meta(base):
            model = model_class

        return Meta

    @classmethod
    def _update_meta(cls, it, instance):
        model_class = instance.__class__
        key = model_class.__name__
        meta_class = cls._meta_cache.get(key, None)
        if meta_class is None:
            cls._meta_cache[key] = meta_class = EntityDetailSerializerBase._get_meta_class(it.Meta, model_class)
        setattr(it, 'Meta', meta_class)

    def __new__(cls, instance, *args, **kwargs):
        it = super(EntityDetailSerializerBase, cls).__new__(cls, instance, *args, **kwargs)
        cls._update_meta(it, instance)
        return it

    def __init__(self, instance, **kwargs):
        kwargs.setdefault('label', 'detail')
        remove_fields = instance._rest_meta.exclude
        include_fields = instance._rest_meta.include
        super(EntityDetailSerializerBase, self).__init__(instance, **kwargs)
        # for multiple fields in a list
        for field_name in remove_fields:
            self.fields.pop(field_name)
        for field_name, field in include_fields.items():
            if isinstance(field, serializers.SerializerMethodField):
                default_method_name = 'get_{field_name}'.format(field_name=field_name)
                if field.method_name is None:
                    method_name = default_method_name
                else:
                    method_name = field.method_name
                    # hack for SerializerMethodField.bind method
                    if field.method_name == default_method_name:
                        field.method_name = None
                method = getattr(instance._rest_meta, method_name)
                setattr(self, method_name, types.MethodType(method, self, self.__class__))
            self.fields[field_name] = field

    def to_representation(self, data):
        """
        Prepare some data for serialization
        """
        self.context['_entity_pk'] = data.id
        return super(EntityDetailSerializerBase, self).to_representation(data)


class EntitySummarySerializer(EntitySummarySerializerBase):
    media = serializers.SerializerMethodField()

    class Meta(EntityCommonSerializer.Meta):
        fields = ('id', 'entity_name', 'entity_url', 'entity_model',
                  'short_characteristics', 'short_marks', 'media')

    def get_media(self, entity):
        return self.render_html(entity, 'media')


class EntityDetailSerializer(EntityDetailSerializerBase):
    media = serializers.SerializerMethodField()

    class Meta(EntityCommonSerializer.Meta):
        exclude = ('active', 'polymorphic_ctype', 'additional_characteristics_or_marks', '_relations', 'terms')

    def get_media(self, entity):
        return self.render_html(entity, 'media')


class EntitySummaryMetadataSerializer(serializers.Serializer):
    data_mart = serializers.SerializerMethodField()
    subj_ids = serializers.SerializerMethodField()
    ordering = serializers.SerializerMethodField()
    potential_terms_ids = serializers.SerializerMethodField()
    real_terms_ids = serializers.SerializerMethodField()

    @staticmethod
    def on_terms_ids_cache_set(key):
        buf = EntityModel.get_terms_cache_buffer()
        old_key = buf.record(key)
        if old_key != buf.empty:
            cache.delete(old_key)

    def get_potential_terms_ids(self, instance):
        tree = self.context['initial_filter_meta']
        initial_queryset = self.context['initial_queryset']
        return initial_queryset.get_terms_ids(tree).cache(on_cache_set=self.on_terms_ids_cache_set,
                                                          timeout=EntityModel.TERMS_IDS_CACHE_TIMEOUT)

    def get_real_terms_ids(self, instance):
        tree = self.context['terms_filter_meta']
        filter_queryset = self.context['filter_queryset']
        return filter_queryset.get_terms_ids(tree).cache(on_cache_set=self.on_terms_ids_cache_set,
                                                         timeout=EntityModel.TERMS_IDS_CACHE_TIMEOUT)

    def get_data_mart(self, instance):
        data_mart = self.context['data_mart']
        if data_mart is not None:
            serializer = DataMartDetailSerializer(data_mart, context=self.context)
            return serializer.data
        return None

    def get_subj_ids(self, instance):
        return self.context['subj_ids']

    def get_ordering(self, instance):
        return self.context['ordering']


class EntityTotalSummarySerializer(serializers.Serializer):
    meta = EntitySummaryMetadataSerializer(source="*")
    objects = EntitySummarySerializer(source="*", many=True)

    def __new__(cls, *args, **kwargs):
        kwargs['many'] = False
        return super(EntityTotalSummarySerializer, cls).__new__(cls, *args, **kwargs)
