# JBOF - A Dataset from Just a Bunch of Files
# Copyright (C) 2018 Bastian Bechtold

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import numpy
import uuid
import json
from pathlib import Path

class DataSet:
    @staticmethod
    def create_dataset(directory, metadata=None, entryformat=None):
        directory = Path(directory)
        directory.mkdir()
        with open(directory / '_metadata.json', 'wt') as f:
            json.dump(dict(metadata, _entryformat=entryformat), f, indent=2)
        with open(directory / '__init__.py', 'wt') as f:
            f.write('import jbof\n')
            f.write('dataset = jbof.DataSet(jbof.Path(__file__).parent)\n')
        return DataSet(directory)

    def __init__(self, directory):
        self.directory = Path(directory)

    @property
    def metadata(self):
        with open(self.directory / '_metadata.json') as f:
            return json.load(f)

    @property
    def _entryformat(self):
        return self.metadata['_entryformat']

    def __getitem__(self, key):
        return self.metadata[key]

    def entryname(self, metadata):
        if isinstance(self._entryformat, str) and '{' in self._entryformat:
            return self._entryformat.format(**metadata)
        elif self._entryformat is None:
            return str(uuid.uuid1())
        else:
            return TypeError(f'entryname must be None, or format string, not {self._entryformat}')

    def entries(self):
        for dir in self.directory.glob('*'):
            if not dir.is_dir() or dir.stem == '__pycache__':
                continue
            yield Entry(dir)

    def create_entry(self, metadata):
        dirname = self.entryname(metadata)
        (self.directory / dirname).mkdir()
        with open(self.directory / dirname / '_metadata.json', 'w') as f:
            json.dump(metadata, f)
        return Entry(self.directory / dirname)


class Entry:
    def __init__(self, directory):
        self.directory = directory

    @property
    def metadata(self):
        with open(self.directory / '_metadata.json') as f:
            return json.load(f)

    def __getitem__(self, key):
        return self.metadata[key]

    def __getattr__(self, name):
        return Datum(self.directory / name + '.json')

    def create_datum(self, name, data, metadata, fileformat='npy'):
        if not fileformat == 'npy':
            raise NotImplementedError('Only npy is supported')

        datafilename = self.directory / (name + '.npy')
        with open(self.directory / (name + '.json'), 'w') as f:
            json.dump(dict(metadata, _filename=str(datafilename)), f, indent=2)
        numpy.save(datafilename, data)

    def all_data(self):
        out = {}
        for meta in self.directory.glob('*.json'):
            if meta.stem == '_metadata':
                continue
            out[meta.stem] = Datum(meta)
        return out


class Datum(numpy.ndarray):
    def __new__(cls, metafile):
        with metafile.open() as f:
            metadata = json.load(f)
        data = numpy.load(metadata['_filename'])
        obj = numpy.asarray(data).view(cls)
        obj.metadata = metadata
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.metadata = getattr(obj, 'metadata', None)
