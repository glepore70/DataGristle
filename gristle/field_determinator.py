#!/usr/bin/env python
""" Purpose of this module is to identify the types of fields
    Classes & Functions Include:
      FieldDeterminator   - class runs all checks on all fields
    Todo:
      - change get_types to consider whatever has 2 STDs 
      - replace get_types freq length logic with something that says, 
        if all types are basically numic, choose float
      - add quartiles, variances and standard deviations
      - add statistical analysis for data quality
      - add histogram to automatically bucketize data
      - consistency metric
      - leverage list comprehensions more
      - consider try/except in get_min() & get_max() int/float conversion
      - change returned data format to be based on field

    See the file "LICENSE" for the full license governing this code. 
    Copyright 2011,2012,2013 Ken Farmer
"""
from __future__ import division
from pprint import pprint

import gristle.field_type   as typer
import gristle.field_math   as mather
import gristle.field_misc   as miscer

#------------------------------------------------------------------------------
# override miscer.get_field_freq max dictionary size defaults:
# The sizes are based on these assumptions:
#   Single col with 10 million unique items, average item length of 20 bytes
#   plus a hashed version of item key, plus two pointers.  That's about 40
#   bytes per entry, or 400 MBytes maximum in this case.
#   Multi-column needs to be more conservative since there could be 10,20, or
#   80 different columns.  So it's limited to 1/10th the number of items.
#------------------------------------------------------------------------------
MAX_FREQ_SINGLE_COL_DEFAULT = 10000000 # ex: 1 col, 10 mil items with 20 byte key = ~400 MB
MAX_FREQ_MULTI_COL_DEFAULT  = 1000000  # ex: 10 cols, each with 1 mil entries & 20 byte key = ~400 MB total


class FieldDeterminator(object):
    """ Examines ALL fields within a file
        Output structures:
          - self.field_names  - dictionary with fieldnumber key
          - self.field_types  - dictionary with fieldnumber key
          - self.field_min    - dictionary with fieldnumber key
          - self.field_max    - dictionary with fieldnumber key
          - self.field_mean   - dictionary with fieldnumber key
          - self.field_median - dictionary with fieldnumber key
          - self.field_case   - dictionary with fieldnumber key
          - self.field_min_length   - dictionary with fieldnumber key
          - self.field_max_length   - dictionary with fieldnumber key
          - self.field_trunc  - dictionary with fieldnumber key
    """

    def __init__(self        ,
                 filename    ,
                 format_type ,
                 field_cnt   ,
                 has_header  ,
                 dialect     ,
                 delimiter=None    ,  # deprecated
                 rec_delimiter=None,  # deprecated
                 verbose=False):
        self.filename            = filename
        self.format_type         = format_type
        self.field_cnt           = field_cnt
        self.has_header          = has_header
        self.dialect             = dialect
        self.verbose             = verbose
        #pp.pprint(locals())
        self.max_freq_number     = None  # will be set in analyze_fields

        #--- public field dictionaries - organized by field_number --- #
        # every field should have a key in every one of these dictionaries
        # but if the dictionary doesn't apply, then the value may be None
        self.field_names         = {}  # all data
        self.field_types         = {}  # all data
        self.field_min           = {}  # all data
        self.field_max           = {}  # all data
        self.field_trunc         = {}  # all data
        self.field_rows_invalid  = {}  # all data

        self.field_mean          = {}  # only for numeric data
        self.field_median        = {}  # only for numeric data
        self.variance            = {}  # only for numeric data
        self.stddev              = {}  # only for numeric data

        self.field_case          = {}  # only for string data
        self.field_max_length    = {}  # only for string data
        self.field_min_length    = {}  # only for string data
        self.field_mean_length   = {}  # only for string data

        #--- public field frequency distributions - organized by field number
        #--- each dictionary has a collection within it:
        self.field_freqs         = {}  # includes unknown values

        assert has_header in [True, False]
        assert 0 < field_cnt < 1000


    def analyze_fields(self,
                       field_number=None,
                       field_types_overrides=None,
                       max_freq_number=None):
        """ Determines types, names, and characteristics of fields.

            Inputs:
               - field_number - if None, then analyzes all fields, otherwise
                 analyzes just the single field (based on zero-offset)
            Outputs:
               - populates public class structures
        """
        self.max_freq_number     = max_freq_number

        if self.verbose:
            print 'Field Analysis Progress: '

        for f_no in range(self.field_cnt):
            if field_number is not None:  # optional analysis of a single field
                if f_no != field_number:
                    continue

            if self.verbose:
                print '   Analyzing field: %d' % f_no

            self.field_names[f_no]   = miscer.get_field_names(self.filename,
                                                              self.dialect,
                                                              f_no)

            if max_freq_number is None:
                if field_number is None:
                    max_items = MAX_FREQ_MULTI_COL_DEFAULT
                else:
                    max_items = MAX_FREQ_SINGLE_COL_DEFAULT
            else:
                max_items = max_freq_number

            (self.field_freqs[f_no],
            self.field_trunc[f_no],
            self.field_rows_invalid[f_no]) = miscer.get_field_freq(self.filename,
                                                            self.dialect,
                                                            f_no,
                                                            max_items)

            self.field_types[f_no]  = typer.get_field_type(self.field_freqs[f_no])
            if field_types_overrides:
                for col_no in field_types_overrides:
                    self.field_types[col_no] = field_types_overrides[col_no]


            self.field_max[f_no]    = miscer.get_max(self.field_types[f_no],
                                              self.field_freqs[f_no])
            self.field_min[f_no]    = miscer.get_min(self.field_types[f_no],
                                              self.field_freqs[f_no])

            if self.field_types[f_no] == 'string':
                self.field_case[f_no]  = miscer.get_case(self.field_types[f_no],
                                                         self.field_freqs[f_no])
                self.field_min_length[f_no]  = miscer.get_min_length(self.field_freqs[f_no])
                self.field_max_length[f_no]  = miscer.get_max_length(self.field_freqs[f_no])
                self.field_mean_length[f_no] = mather.get_mean_length(self.field_freqs[f_no])
            else:
                self.field_case[f_no]        = None
                self.field_min_length[f_no]  = None
                self.field_max_length[f_no]  = None
                self.field_mean_length[f_no] = None


            if self.field_types[f_no] in ['integer','float']:
                self.field_mean[f_no]   = mather.get_mean(self.field_freqs[f_no])
                self.field_median[f_no] = mather.GetDictMedian().run(self.field_freqs[f_no])
                (self.variance[f_no], self.stddev[f_no])   \
                   =  mather.get_variance_and_stddev(self.field_freqs[f_no],
                                                     self.field_mean[f_no])
            else:
                self.field_mean[f_no]   = None
                self.field_median[f_no] = None
                self.variance[f_no]     = None
                self.stddev[f_no]       = None

    def get_known_values(self, fieldno):
        """ returns a frequency-distribution dictionary that is the
            self.field_freqs with unknown values removed.
        """

        return [val for val in self.field_freqs[fieldno]
                if typer.is_unknown(val) is False]


    def get_top_freq_values(self,
                            fieldno,
                            limit=None):
        """  Returns a list of highest-occuring field values along with their
             frequency.
             Args:
                 - fieldno - is the number of the field, offset from zero
                 - limit - is an optional limit on the number of values to show
             Returns:
                 - rev_sort_list, which is a list of lists.
                   - The inner list is the [field value, frequency]
                   - The outer list contains up to limit number of inner lists,
                     sorted by innerlist, frequency, descending.
                   - For example, the following hypothetical results would be
                     returned for a field that describes the number of failing
                     schools by state with
                     a limit of 3:
                        [['ca',120],
                         ['ny',89],
                         ['tx',71]]
             Issues:
                   - need to test with array with just 1 row, seems to be blowing up
                     probably an off by 1 error, no time to diagnose now.
        """
        sort_list = sorted(self.field_freqs[fieldno],
                           key=self.field_freqs[fieldno].get)
        sub           = len(sort_list) - 1
        count         = 0
        rev_sort_list = []
        while sub >= 0:
            freq  = self.field_freqs[fieldno][sort_list[sub]]
            rev_sort_list.append([sort_list[sub], freq])
            count += 1
            sub   -= 1
            if limit is not None:
                if count >= limit:
                    break

        return rev_sort_list


class IOErrorEmptyFile(IOError):
    """Error due to empty file
    """
    pass


