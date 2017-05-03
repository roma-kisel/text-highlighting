"""Module contains classes and functions to work with SYN format file"""


import re
from collections import OrderedDict


__author__    = 'Roman Kiselevich (xkisel00@stud.fit.vutbr.cz)'


class FormatFileError(Exception):
    """

    Represent errors (syntax, semantic etc.)
    which can occur in the format file

    """
    _base_msg = 'format file: '

    def __init__(self, errmsg):
        """Initialize error object with error message"""
        self.errmsg = errmsg

    def __str__(self):
        return FormatFileError._base_msg + self.errmsg


def _normalize_regex(regex):
    """

    Convert IFJ regex to python regex. Regexes are
    in string representation

    """
    special_symbols = '.|!*+()%'
    saved_regex = regex

    if re.search(r'(?<!%)\.\.+', regex):
        saved_regex = '\'{0}\''.format(saved_regex)
        raise FormatFileError('invalid regex ' + saved_regex)

    regex = re.sub(r'(?<!%)\.', '', regex)
    regex = re.sub(r'(\[|\])', r'\\\1', regex)

    regex = re.sub(r'\\([dAbBDsSwWZ])', r'[\\\\\\][\1]', regex)
    regex = re.sub(r'\\([ntrvxab\\])', r'\\\\\1', regex)
    regex = re.sub(r'([\^\$\{\}\?])', r'\\\1', regex)

    regex = re.sub(r'%s', r'[\s]', regex)
    regex = re.sub(r'%a', r'[\W\w]', regex)
    regex = re.sub(r'%d', r'[\d]', regex)
    regex = re.sub(r'%l', r'[a-z]', regex)
    regex = re.sub(r'%L', r'[A-Z]', regex)
    regex = re.sub(r'%w', r'[a-zA-Z]', regex)
    regex = re.sub(r'%W', r'[a-zA-Z\d]', regex)
    regex = re.sub(r'%t', r'[\t]', regex)
    regex = re.sub(r'%n', r'[\n]', regex)

    for match in re.finditer(r'(?<!!)%(.)', regex):
        if match.group(1) in special_symbols:
            regex = match.re.sub(r'[\1]', regex)
        else:
            saved_regex = '\'{0}\''.format(saved_regex)
            raise FormatFileError('invalid regex ' + saved_regex)

    regex = re.sub(r'!\[', r'[^', regex)
    regex = re.sub(r'(?<!\[)!(.)(?!\])', r'[^\1]', regex)

    try:
        return re.compile(regex)
    except Exception:
        saved_regex = '\'{0}\''.format(saved_regex)
        raise FormatFileError('invalid regex !!! ' + saved_regex)


def _get_param_list(params):
    """

    Convert a parametr list string representation to corresponding
    python RegexParam objects list and return it as a result
    
    Params here for example can be a string 'bold, italic, size:7'

    """
    param_list = []
    for param in re.split(r',[\t ]+', params):
        match = re.match(r'^(\w+)(?::(\w+))?$', param)
        if not match:
            if match is None:
                raise FormatFileError(
                    'param or attribute cannot be empty'
                )
            else:
                raise FormatFileError('invalid param ' + match.group(0))

        try:
            param = RegexParam(match.group(1), match.group(2))
        except FormatFileError as e:
            raise e
        else:
            param_list.append(param)

    return param_list


class RegexParam:
    """

    Represent IFJ regex parametr like for example bold, italic, size:7

    """
    names = ('bold', 'italic', 'underline', 'teletype')
    names_with_attr = ('size', 'color')
    map_tag = {
        'bold': ('<b>', '</b>'),
        'italic': ('<i>', '</i>'),
        'underline': ('<u>', '</u>'),
        'teletype': ('<tt>', '</tt>'),
        'size': ('<font size=*>', '</font>'),
        'color': ('<font color=#*>', '</font>')
    }

    def __init__(self, name, attr=None):
        """

        Initialize RegexParam object with corresponding name
        and attribute

        """
        if name in RegexParam.names:
            if not attr:
                self.name = name
                self.attr = None
                self.open_tag = RegexParam.map_tag[self.name][0]
                self.close_tag = RegexParam.map_tag[self.name][1]
            else:
                name = "\'{0}\'".format(name)
                raise FormatFileError(
                    'param ' + name + ' doesn\'t have an attribute')
        elif name in RegexParam.names_with_attr:
            if not attr:
                name = "\'{0}\'".format(name)
                raise FormatFileError(
                    'param ' + name + 'require an attribute')

            if name == 'size' and not re.match(r'^[1-7]$', attr):
                raise FormatFileError(
                    '\'size\' attribute should be a number in [1-7]')
            elif (name == 'color' and
                not re.match(r'^[0-9ABCDEF]{6}$', attr)):

                raise FormatFileError(
                    '\'color\' attribute should be a ' +
                    'hex number in [000000-FFFFFF]')

            self.name = name
            self.attr = attr
            self.open_tag = re.sub(
                r'\*', self.attr, RegexParam.map_tag[self.name][0])
            self.close_tag = RegexParam.map_tag[self.name][1]
        else:
            name = "\'{0}\'".format(name)
            raise FormatFileError('invalid param ' + name)


class FormatFile:
    """

    Represent SYN format file. Each object contains dictionary
    {RegexObject: [RegexParam, RegexParam, ...]} and for the best
    readability that dictionary elements can be accessed using
    wrapper methods described below

    """
    def __init__(self, filename):
        """Initializes FormatFile object"""
        self._re_param_map = OrderedDict()
        self.name = filename
        try:
            with open(filename, encoding='utf-8') as format_file:
                for line in format_file:
                    fmt_line_pattern = r'^([^\t]+)\t+(\w[\w, \t:]+)\n?$'
                    match = re.match(fmt_line_pattern, line)
                    if not match:
                        raise FormatFileError('syntax error')
                    
                    try:
                        norm_re_obj = _normalize_regex(match.group(1))
                        param_list = _get_param_list(match.group(2))
                    except FormatFileError as e:
                        raise e
                    else:
                        self._re_param_map[norm_re_obj] = param_list
        except IOError as io_error:
            io_error.strerror = 'cannot open file for reading'
            raise io_error
        except FormatFileError as synt_error:
            raise synt_error

    def __iter__(self):
        """Wrapper method to access format file elements"""
        return self._re_param_map.__iter__()

    def __next__(self):
        """Wrapper method to access format file elements"""
        return self._re_param_map.__next__()

    def __reversed__(self):
        """Wrapper method to access format file elements"""
        return self._re_param_map.__reversed__()

    def __getitem__(self, key):
        """Wrapper method to access format file elements"""
        return self._re_param_map[key]

    def __setitem__(self, key, value):
        """Wrapper method to access format file elements"""
        self._re_param_map[key] = value

    def __delitem__(self, key):
        """Wrapper method to access format file elements"""
        del self._re_param_map[key]

    def __missing__(self, nonexistent_key):
        """Wrapper method to access format file elements"""
        nonexistent_key = '\'{0}\''.format(nonexistent_key)
        raise Exception('regex ' + nonexistent_key + 'doesn\'t exist')
