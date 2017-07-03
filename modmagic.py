# -*- coding: UTF-8 -*-
#
# Copyright (c) 2017, Yung-Yu Chen <yyc@solvcon.net>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the copyright holder nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""IPython mod(ule) magic."""


from __future__ import print_function


import os
import sys
import imp
import collections
import argparse

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

from IPython.core.magic import Magics, magics_class, line_cell_magic
from IPython.display import display, HTML


# publish the CSS for pygments highlighting
display(HTML("""
<style type='text/css'>
%s
</style>
""" % HtmlFormatter().get_style_defs()
))


def load_ipython_extension(ipython):
    ipython.register_magics(ModMagics)


class ModContent(object):
    def __init__(self, fullname, mod, source, line=None):
        super(ModContent, self).__init__()
        self.fullname = fullname
        self.mod = mod
        self.source = source
        self.line = line
        
    @property
    def name(self):
        return fullname.split('.')[-1]

@magics_class
class ModMagics(Magics):
    """Turn a cell into a module."""
    
    def __init__(self, shell=None, **kw):
        if shell is None:
            shell = get_ipython()            
        super(ModMagics, self).__init__(shell, **kw)
        self.contents = collections.OrderedDict()

    def _create_parents(self, fullname):
        """Create parent module objects so that "from a.b import c" may be
        used."""
        names = fullname.split('.')
        for it in range(len(names)):
            pname = '.'.join(names[:it+1])
            if pname not in sys.modules:
                sys.modules[pname] = imp.new_module(pname)
        for it in range(len(names)-1, -1, -1):
            pname = '.'.join(names[:it])
            cname = '.'.join(names[:it+1])
            if pname:
                pmod = sys.modules[pname]
                setattr(pmod, names[it], sys.modules[cname])
        
    def _build_module(self, tokens, cell):
        """Build a module from cell.
        
        If multiple cells have tagged as the same module, those cells are
        incrementally built into the module.  The source code is concatenated
        to the ModContent.
        
        Nested module is OK."""
        name = tokens[0]
        if len(tokens) == 1:
            fullname = tokens[0]
        elif len(tokens) == 3 and tokens[1] == 'in':
            fullname = '.'.join([tokens[2], tokens[0]])
        else:
            print('usage: %%mod build name [in parent_package]')
            return

        # retrieve content module.
        content = self.contents.get(fullname, None)
        if not content:
            if len(tokens) == 1:
                line = '%%%%mod build %s' % fullname
            else:
                line = '%%%%mod build %s in %s' % (tokens[0], tokens[2])
            content = ModContent(
                fullname, imp.new_module(fullname), cell, line=line)
        else:
            content.source += cell
        mod = content.mod

        # compile the module.
        exec(cell, mod.__dict__)
        self.contents[fullname] = content
        
        # module namespace.
        sys.modules[fullname] = mod
        self._create_parents(fullname)

        # notebook shell namespace.
        shell_names = {name: mod}
        top_name = fullname.split('.')[0]
        if top_name != name:
            shell_names[top_name] = sys.modules[top_name]
        self.shell.push(shell_names)

    def _list_modules(self):
        """List all modules managed by this magic."""
        print(list(self.contents.keys()))

    def _show_module(self, name):
        """Show the module content."""
        ent = self.contents.get(name, None)
        if not ent:
            ent = dict((ent.name, ent.mod)
                       for ent in self.contents).get(name, None)
        if ent:
            formatter = HtmlFormatter()
            lexer = PythonLexer()
            source = '# %s\n%s' % (ent.line, ent.source)
            html = highlight(source, lexer, formatter)
            display(HTML(html))
        else:
            print('no module named %s' % name)

    @line_cell_magic
    def mod(self, line, cell=None):
        tokens = line.split()
        if cell is None:
            # %module list
            if len(tokens) > 0 and tokens[0] == 'list':
                self._list_modules()
            # %module show mod_name
            elif len(tokens) == 2 and tokens[0] == 'show':
                self._show_module(tokens[1])
            else:
                print('usage: %mod list')
                print('            show mod_name')
                return
        else:
            # %%module build ...
            if len(tokens) > 0 and tokens[0] == 'build':
                self._build_module(tokens[1:], cell)
            else:
                print('usage: %%mod build name [in parent_package]')
                return
