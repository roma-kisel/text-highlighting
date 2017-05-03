"""IPP 2016/2017 Project 2

Script highlights some parts of input text using html tags. Information
about highlighting is stored in the format file which contains regexes
and their format parameters in the following way:
    
    IFJ-regex1<HT+>[param_list1]<LF>
    IFJ-regex2<HT+>[param_list2]<LF>
    ...
    IFJ-regexn<HT+>[param_listn]<LF>?

HT - (horizontal tab) LF - (new line)
[param_list] is list of parametrs which are represents html tags and
it must be specified in the following way:

    param1, param2, param3 ... etc.

Parameters must be separated from each other by comma followed by any
number of spaces or horizontal tabs

Some parameters can take a value that must be specified in this way

    param:value

The following table contains available parameters, their values and
corresponding open tags:

| Parameter | value                               | open_tag       |
|-----------|-------------------------------------|----------------|
| bold      | no                                  | <b>            |
| italic    | no                                  | <i>            |
| underline | no                                  | <u>            |
| teletype  | no                                  | <tt>           |
| size      | number in range [1-7]               | <font size=*>  |
| color     | hex number in range [000000-FFFFFF] | <font color=*> |

* - is a parametr value

Available script options:

    --help            print this message
    --input=filename  specify input file (stdin if option wasn't passed)
    --output=filename specify output file (stdout if option wasn't passed)
    --format=filename specify format file
    --br              insert <br /> tag before each LF char

"""


import sys
import os
import re
from getopt import getopt
from getopt import GetoptError
from collections import deque

from ipp_syn import exit_codes
from ipp_syn.format_file import FormatFile
from ipp_syn.format_file import FormatFileError


__author__    = 'Roman Kiselevich (xkisel00@stud.fit.vutbr.cz)'


def error_print(*args, **kwargs):
    """Is similar like print() but print message to stderr"""
    print(*args, file=sys.stderr, **kwargs)


def get_args():
    """Returns program options as dictionary {'option': value}"""
    opts_dictionary = {}
    try:
        options, args = getopt(sys.argv[1:], '', 
                ['help', 'input=', 'output=', 'br', 'format='])

        if args: # args list is not empty
            raise GetoptError(
                'invalid program argument \'' + args[0] + '\'')
       
        opts_list = [opt[0] for opt in options]
        if len(opts_list) != len(set(opts_list)):
            raise GetoptError('cannot combine two or more same options')

        for arg in sys.argv[1:]:
            if (arg[2:] != 'help' and arg[2:] != 'br' and
                not re.match(r'\w+=.+', arg[2:])):
                raise GetoptError('bad option \'' + arg + '\'')
    except GetoptError as opt_error:
        error_print(sys.argv[0], ': ', end='', sep='')
        error_print(opt_error)
        sys.exit(exit_codes.BAD_ARGUMENTS)

    for opt in options:
        opts_dictionary[opt[0][2:]] = opt[1]
            
    return opts_dictionary


if __name__ == '__main__':
    opts = get_args()

    if 'help' in opts:
        print(re.sub(r'\n', r'\n    ', __doc__))
        sys.exit(exit_codes.SUCCESS)

    if 'input' in opts:
        try:
            input_file = open(opts['input'], encoding='utf-8')
            input_file_content = input_file.read()
            input_file.close()
        except IOError as io_error:
            io_error.strerror = 'cannot open file for reading'
            error_print(sys.argv[0], io_error.strerror, sep=': ', end=' ')
            io_error.filename = '\'{0}\''.format(io_error.filename)
            error_print(io_error.filename)
            sys.exit(exit_codes.BAD_INPUT)
    else:
        input_file_content = sys.stdin.read()

    if 'output' in opts:
        try:
            output_file = open(opts['output'], 'wt', encoding='utf-8')
        except IOError as io_error:
            io_error.strerror = 'cannot open file for writing'
            error_print(sys.argv[0], io_error.strerror, sep=': ', end=' ')
            io_error.filename = '\'{0}\''.format(io_error.filename)
            error_print(io_error.filename)
            sys.exit(exit_codes.BAD_OUTPUT)
    else:
        output_file = sys.stdout

    if 'format' in opts:
        try:
            format_file = FormatFile(opts['format'])
        except IOError as io_error:
            output_file.write(input_file_content)
            output_file.close()
            sys.exit(exit_codes.SUCCESS)
        except FormatFileError as format_error:
            error_print(sys.argv[0], format_error, sep=': ')
            output_file.close()
            sys.exit(exit_codes.BAD_FORMAT)
    else:
        if 'br' in opts:
            input_file_content = re.sub(
                r'\n', '<br />\n', input_file_content)

        output_file.write(input_file_content)
        output_file.close()
        sys.exit(exit_codes.SUCCESS)
    
    if os.path.getsize(format_file.name) == 0: # format file is empty
        if 'br' in opts:
            input_file_content = re.sub(
                r'\n', '<br />\n', input_file_content)

        output_file.write(input_file_content)
        output_file.close()
        sys.exit(exit_codes.SUCCESS)

    pos_tag_deque = deque()
    close_tags = []
    for regex in format_file:
        for match in regex.finditer(input_file_content):
            if not match.group(0):
                continue

            for param in format_file[regex]:
                pos_tag_deque.append((match.start(), param.open_tag)) 
                close_tags.append((match.end(), param.close_tag))
    
    for close_tag in reversed(close_tags):
        pos_tag_deque.append(close_tag)

    del close_tags
    pos_tag_deque = deque(
        sorted(pos_tag_deque,
            key=lambda pos_tag: 
                (pos_tag[0], pos_tag[1][1]) if pos_tag[1][1] == '/' 
                        else (pos_tag[0], pos_tag[1][0])
        )
    )

    for index, char in enumerate(input_file_content):
        while pos_tag_deque and index == pos_tag_deque[0][0]:
            output_file.write(pos_tag_deque[0][1])
            pos_tag_deque.popleft()
            
        if char == '\n' and 'br' in opts:
            output_file.write('<br />')

        output_file.write(char)

    while pos_tag_deque:
        output_file.write(pos_tag_deque[0][1])
        pos_tag_deque.popleft()

    output_file.close()
