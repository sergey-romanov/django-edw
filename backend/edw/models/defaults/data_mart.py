# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
"""
"""
from edw.models.data_mart import BaseDataMart, BaseDataMartManager


class DataMartManager(BaseDataMartManager):
    pass


class DataMart(BaseDataMart):
    """
    Default materialized model for DataMart containing common fields
    """
    ORDER_BY_NAME_ASC = 'name'
    # ORDER_BY_NAME_DESC = '-name'

    ORDERING_MODES = (
        (ORDER_BY_NAME_ASC, _('Alphabetical')),
        # (ORDER_BY_NAME_DESC, _('Alphabetical: descending')),
    ) + BaseDataMart.ORDERING_MODES

    objects = DataMartManager()

    class Meta:
        abstract = False
        verbose_name = _("Data mart")
        verbose_name_plural = _("Data marts")