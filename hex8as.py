#!/usr/bin/env python
"""
    
    hex8as.py - A Python based assembler for Hex8

    Copyright (C) 2014 Steve Kerrison, University of Bristol,
        <steve.kerrison@bristol.ac.uk>

    Golf buddy: James Pallister

Usage:
    hex8as.py [options] <file>

Options:
    -o <hexfile>            Output hex file [default: a.hex]
    -b <bytes>              Num. bytes per line [default: 8]

Arguments:
    <file>                  Input assembly file

"""

"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from docopt import docopt
import re


class Hex8as:

    """
        A semi-clever assembler for the hex8 ISA, following the method defined
        in the lecture material for the UoB CS COMSM1302 unit
    """
    # List index infers instruction encoding (ldam = 0, ldbm = 1, ... )
    imap = ['ldam', 'ldbm', 'stam', 'ldac', 'ldbc', 'ldap', 'ldai', 'ldbi',
            'stai', 'br', 'brz', 'brn', 'brb', 'add', 'sub', 'pfx']

    def __init__(self, filename):
        self.filename = filename
        self.asm = []

    def read(self):
        """
            Read asm file, strip out comments and canonicalise format
        """
        self.asm = [
            dict(
                list({
                     'label': self.get_label(x[0]),
                     'instr': x[1].lower(),
                     'op_raw': x[2],
                     }.items()) +
                list(self.get_operand(x[2]).items())
            ) for x in map(lambda(x): map(lambda(y): y.strip(), x),
                           re.findall(r'\s*(\w+\:)?\s*(\w+)([^\w\n]+\w+)?',
                                      re.subn(r'[;#].*', '',
                                              open(self.filename, 'r').read(),
                                              re.M)[0],
                                      re.M)
                           )
        ]
        self.update_ldic()
        return self

    def insert_prefix(self, addr, immediate):
        """
            Insert a prefix if required. Returns True if the assembly table was
            modified.
        """
        if immediate is None:
            return False
        if immediate & 0xf0 == 0:
            return False
        if addr == 0 or self.asm[addr - 1]['instr'] != 'pfx':
            """
                If the asm author put a prefix in manually before
                this instruction, it'll get overwritten. To avoid
                this, they should not use labels in branches, or
                specify over-size immediates
            """
            self.asm.insert(addr, {
                'instr': 'pfx',
                'op_num': 0,
                'op_raw': '0',
                'label': None,
            })
            if self.asm[addr + 1]['label']:
                # Move the label to the prefix
                self.asm[addr]['label'] = self.asm[addr + 1]['label']
                self.asm[addr + 1]['label'] = None
            self.update_ldic()
            return True
        return False

    def resolve_immediates(self):
        """
            Looks for large immediates and labels, attempting to insert
            prefixes, then produce appropriate immediate operands.
        """
        while True:
            run = False
            for addr, asm in enumerate(self.asm):
                immediate = None
                if asm['instr'] == 'data':
                    continue
                if asm['op_num'] is None:
                    tgt = self.ldic[asm['op_raw']]
                    immediate = tgt - addr - 1
                elif asm['op_num'] is not None:
                    immediate = asm['op_num']
                if self.insert_prefix(addr, immediate):
                    run = True
                    break
            # If run is true, new asm was inserted, so loop again
            if run:
                continue
            # asm is stable now, so populate final immediate values
            for addr, asm in enumerate(self.asm):
                immediate = None
                if asm['instr'] == 'data':
                    continue
                if asm['op_num'] is None:
                    tgt = self.ldic[asm['op_raw']]
                    immediate = tgt - addr - 1
                elif asm['op_num'] is not None:
                    immediate = asm['op_num']
                if immediate & 0xf0:
                    self.asm[addr - 1]['op_num'] = (immediate >> 4) & 0xf
                if immediate is not None:
                    asm['op_num'] = immediate & 0xf
            break
        return self

    def update_ldic(self):
        """
            Generate new list of label locations.
        """
        self.ldic = {
            v['label']: k for k, v in enumerate(self.asm) if v['label']
        }

    def write(self, filename, bpl):
        """
            Do a little interpretation and then output the final asm hex
        """
        ofile = open(filename, 'w')
        bpl = int(bpl, 0)
        bc = 0
        for line in self.asm:
            bc += 1
            if bc > 1 and bc <= bpl:
                ofile.write(' ')
            elif bc > bpl:
                ofile.write('\n')
                bc = 1
            if line['instr'] == 'data':
                ofile.write('{:02x}'.format(line['op_num']))
            else:
                ofile.write('{:x}{:x}'.format(
                    self.imap.index(line['instr']), line['op_num']))
        ofile.write('\n')

    def assemble(self):
        """
            Do everything except the final translation and output to machine
            code
        """
        return self.read().resolve_immediates()

    @staticmethod
    def get_label(opr):
        """
            Determine if line of assembly is labelled, if so, tidy up
        """
        if opr == '':
            return None
        else:
            return opr[:-1]

    @staticmethod
    def get_operand(opr):
        """
            See if we can parse an int, otherwise operand is empty or label
        """
        try:
            return {'op_num': int(opr, 0)}  # Auto-parse common number formats
        except ValueError:
            if opr == '':
                return {'op_num': 0}  # Implicit zero operand
            else:
                return {'op_num': None}  # Still to be resolved

if __name__ == '__main__':
    ARGS = docopt(__doc__)
    H8 = Hex8as(ARGS['<file>'])
    H8.assemble().write(ARGS['-o'], ARGS['-b'])

