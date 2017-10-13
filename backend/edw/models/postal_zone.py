# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.utils.six import with_metaclass
from . import deferred
from .term import TermModel


# =========================================================================================================
# PostalZone
# =========================================================================================================
@python_2_unicode_compatible
class BasePostZone(with_metaclass(deferred.ForeignKeyBuilder, models.Model)):
    '''
    Related to Term postal zones
    '''
    term = models.ForeignKey(TermModel, verbose_name=_('Term'), related_name='+', db_index=True)
    postal_codes = models.TextField(verbose_name=_('Postal codes'), null=True, blank=True, help_text=_(
        """You enter on one index in line. Use '?' and '*' as universal substitutes. """
        """'?' replaces any symbol, '*' replaces any sequence of symbols (including I am empty). """
        """Gaps are ignored. '_' replaces any quantity of gaps (but at least one). """
        """Example: 2204*, 38?45, 23*, 123_4??."""))

    active = models.BooleanField(verbose_name=_('Active'), default=True, db_index=True)

    class Meta:
        abstract = True
        verbose_name = _("Postal zone")
        verbose_name_plural = _("Postal zones")
        unique_together = (('term', 'active'),)
        ordering = ('term__{}'.format(TermModel._mptt_meta.tree_id_attr), 'term__{}'.format(TermModel._mptt_meta.left_attr))

    def __str__(self):
        return self.name

    @property
    def name(self):
        if self.term.parent_id is not None:
            return "{} - {}".format(self.term.parent.name, self.term.name)
        else:
            return "{}".format(self.term.name)
    name.fget.short_description = _('Name')

    @cached_property
    def code_pattern(self):
        raw_patterns = re.split(r'\s+', self.postal_codes.strip())
        patterns = [re.sub(r'_+', '\s+', re.sub(r'\*', '.*?', re.sub(r'\?', '.', x))) for x in raw_patterns]
        return r'^(?:%s)$' % '|'.join(patterns)

    def is_postal_code_match(self, code):
        return re.match(self.code_pattern, code) is not None

PostZoneModel = deferred.MaterializedModel(BasePostZone)

def get_postal_zone(postcode):
    tree_opts = TermModel._mptt_meta
    zones = PostZoneModel.objects.filter(active=True).order_by(
        '-' + 'term__{}'.format(tree_opts.level_attr),
        'term__{}'.format(tree_opts.tree_id_attr), 'term__{}'.format(tree_opts.left_attr))
    for zone in zones:
        if zone.is_postal_code_match(postcode):
            break
    else:
        zone = None
    return zone