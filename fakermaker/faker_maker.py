# Author: Nicholas Miller (miller.nicholas.a@gmail.com)
# Created: 2020-09-23
# https://github.com/cassova/Faker-Maker

from IPython.core.magic import (Magics, magics_class, register_cell_magic,
                                line_cell_magic, needs_local_scope)
import numpy as np
import pandas as pd
from faker import Faker
import random
import re

class FakeDataFrameParserException(Exception):
    pass

class FakeDataFrameAssembleException(Exception):
    pass

class FakeDataFrameBuilder():
    __faker = Faker()
    __lines = []
    __reference_dict = {}
    __default_dataframe_size = 99
    __seed = np.NaN
    __field_matcher = """
        ^(?P<function_to_call>[\w]+)
        (\s*\((?P<parameters>[\w=\-\'\.]+(,[\w=\-\'\.]+)*)\))*
        (\s+as\s+(?P<field_name>\w+))*
        (\s+\[(?P<reference>[\d,]+)\])*
        (\s*(?P<unique_mark>\*))*
        (\s+\#(?P<comment>.*))*$
    """
    
    repeat_threshold = 0.25    # Try to repeat values 20% of the time
    dataframes = {}
    
    def __init__(self):
        pass
        
    def __init__(self, text_blob, lang="en_US"):
        self.__faker = Faker(lang)
        self.__lines = text_blob.split('\n')

    def seed(self, s):
        self.__seed = s
        self.__faker.seed_instance(s)
        random.seed(s)
        np.random.seed(s)
        
    
    def __get_faker_data(self, function_name, params):
        func_to_run = getattr(self.__faker, function_name)
        return func_to_run(**params)
    
    def __assemble_reference_column(self, references, field, details, unique_fields, size):
        func = details['function_to_call']
        args = details['parameters']
        result = []
        
        # First identify which table it is we're working on
        for r in references.split(','):
            ref_list = self.__reference_dict[r]
            for d in ref_list:
                # Check if an already built table contains our reference (is in ref_list)
                try:
                    # Don't like how this is seeded:
                    #return self.dataframes[d[0]][d[1]].sample(n=size, random_state=self.__seed).to_list()
                    return random.choices(self.dataframes[d[0]][d[1]].to_list(),k=size)
                except:
                    pass
            # if we got here, we couldn't find a df with any reference values so just generate new values
            if field in unique_fields:
                return self.__assemble_unique_column(field, details, size)
            else:
                return self.__assemble_standard_column(field, details, size)
    
    def __assemble_unique_column(self, field, details, size):
        func = details['function_to_call']
        args = details['parameters']
        result = []
        
        for i in np.arange(size):
            # If we have a unique violation, we will attempt again up to a max of this # of times
            max_unique_checks = 10
            unique_count = 0
            while True:
                # Loop until we find a unique value or run out of tries
                value = self.__get_faker_data(func, args)
                if unique_count >= max_unique_checks:
                    raise FakeDataFrameAssembleException('Maxed out unique checks for field {field}')
                elif value in result:
                    #print(f'Found Duplicate for field {field} with value {value}')
                    unique_count += 1
                else:
                    break
            result.append(value)
        return result
    
    def __assemble_standard_column(self, field, details, size):
        func = details['function_to_call']
        args = details['parameters']
        result = []
        
        # (A-Group) Start building a list of random values
        asize = np.floor(size * (1-self.repeat_threshold))
        for i in np.arange(asize):
            result.append(self.__get_faker_data(func, args))
            
        # Let's see how unique our A-group is before we start our overlap pass
        # If not all values our unique, let's salt it so we hopefully endup closer to our
        # random threshold value
        asize_salt = 0
        unq = []
        unq_perc = 1 - len([unq.append(x) for x in result if x not in unq]) / len(result)
        if unq_perc > 0:
            if unq_perc > self.repeat_threshold:
                asize_salt = size - asize
            else:
                asize_salt = np.floor(unq_perc * asize)
            #print(f'Field {field} is {unq_perc} unique and will get {asize_salt} more values')
            for i in np.arange(asize_salt):
                result.append(self.__get_faker_data(func, args))
        
        # (B-Group) Sample from our existing list to ensure we get an overlap of data (e.g. duplicates)
        bsize = size - asize - asize_salt
        for i in np.arange(bsize):
            result.append(random.sample(result,1)[0])
            
        random.shuffle(result)
        return result
        
    def __assemble_dataframe(self, name, size, fields):
        # Identify which fields are unique
        unique_fields = [k for k,v in fields.items() if v['unique_mark'] == '*']
        
        # Here we will create our dictionary that contains our fake data to be put into DataFrames
        dataframe_dict = {}
        for field, details in fields.items(): # loop over each field
            if details['reference'] is not None:
                dataframe_dict[field] = self.__assemble_reference_column(details['reference'], field, details,
                                                                         unique_fields, size)
            elif field in unique_fields:
                dataframe_dict[field] = self.__assemble_unique_column(field, details, size)
            else:
                dataframe_dict[field] = self.__assemble_standard_column(field, details, size)
        self.dataframes[name] = pd.DataFrame(dataframe_dict)
    
    def __parse_parameters(self, params):
        # This will build a parameter dictionary
        # Example: my_func('first',2=2,third=3,4) --> {0: "'first'", '2': 2.0, 'third': 3.0, 3: 4.0}
        if params is None:
            return {}
        else:
            param_split = params.split(',')
            param_dict = {}
            for i, param in enumerate(param_split):
                parts = re.match(r'^((?P<key>[\w\-]+)\=)*(?P<value>[\w\-\.]+|\'[\w\-\.]+\')$', param)
                if parts is None:
                    raise FakeDataFrameParserException(f'Unparsable parameter: {param}')
                key = parts.groupdict()['key']
                if key is None:
                    key = i
                # check if the value contains only numbers, if so, convert to number
                if re.match(r'^[\d\.]+$', parts.groupdict()['value']):
                    param_dict[key] = float(parts.groupdict()['value'])
                else:
                    param_dict[key] = parts.groupdict()['value']
        #print (f'Parameters = {param_dict}')
        return param_dict
    
    def __parse_reference(self, reference, table, field):
        for r in reference.split(','):
            try:
                ref_list = self.__reference_dict[r] 
                ref_list.append((table, field))
            except:
                self.__reference_dict[r] = [(table, field)]
    
    def parse(self):
        if len(self.__lines) < 2:
            raise FakeDataFrameParserException('Not enough lines to process')
        
        new_dataframe_name = ""
        new_dataframe_size = 0
        new_dataframe_fields = {}
        next_is_header = True
        next_is_seperator = False
        
        for line in self.__lines:
            if next_is_header:
                # Handle extra whitespace or comments between dataframe definitions
                parts = re.match(r'^\s*(\#.*)*$', line)
                if parts is None:
                    # Here we're expecting a header (i.e. a dataframe name)
                    parts = re.match(r'^(?P<name>[\w]{1}[\w\-]+)(\s*{(?P<size>\d+)\})*(?P<comment>(\s+[#]{1}.*|\s*)$)', line)
                    if parts is None:
                        raise FakeDataFrameParserException(f'Unparsable header line: {line}')
                    new_dataframe_name = parts.groupdict()['name']
                    if parts.groupdict()['size'] is None:
                        new_dataframe_size = self.__default_dataframe_size
                    else:
                        new_dataframe_size = int(parts.groupdict()['size'])
                    next_is_header = False
                    next_is_seperator = True
            elif next_is_seperator:
                parts = re.match(r'^(?P<sep>[\-]{2,})(?P<comment>(\s+[#]{1}.*|\s*)$)', line)
                if parts is None:
                    raise FakeDataFrameParserException(f'Unparsable seperator line: {line}')
                next_is_seperator = False
            else: # We either have a field or empty line
                parts = re.match(r'^\s*$', line)
                if parts is not None:
                    # We have an empty line so we'll assume this dataframe definition is done - could be smarter
                    if len(new_dataframe_fields) < 1:
                        raise FakeDataFrameParserException(f'Unexpected empty dataframe: {new_dataframe_name}')
                    self.__assemble_dataframe(new_dataframe_name, new_dataframe_size, new_dataframe_fields)
                    
                    # Clear our values
                    new_dataframe_name = ""
                    new_dataframe_fields = {}
                    next_is_header = True
                else:
                    # This a field line
                    if re.match(r'^#', line):
                        pass
                    else:
                        # Here we're expecting a field definition
                        parts = [item.groupdict() for item in re.finditer(self.__field_matcher,line,re.VERBOSE)]
                        if len(parts) < 1:
                            raise FakeDataFrameParserException(f'Unparsable field line: {line}')
                        else:
                            if parts[0]['field_name'] is None:
                                # Here we'll assume the field name is the function_to_call
                                i = 1
                                field_name = parts[0]['function_to_call']
                                while True:
                                    # If we have the same function defined multiple times, we'll give a unique name
                                    if field_name in new_dataframe_fields.keys():
                                        field_name = parts[0]['function_to_call'] + str(i)
                                        i += 1
                                    else:
                                        break
                            else:
                                field_name = parts[0]['field_name']
                            del parts[0]['field_name']
                            parts[0]['parameters'] = self.__parse_parameters(parts[0]['parameters'])
                            if parts[0]['reference'] is not None:
                                self.__parse_reference(parts[0]['reference'], new_dataframe_name, field_name)
                            new_dataframe_fields[field_name] = parts[0]
                        
        # All done with our for-loop, let's call assemble if we have an unassembled dataframe
        if len(new_dataframe_name) > 0:
            if len(new_dataframe_fields) < 1:
                raise FakeDataFrameParserException(f'Unexpected empty dataframe: {new_dataframe_name}')
            self.__assemble_dataframe(new_dataframe_name, new_dataframe_size, new_dataframe_fields)
        
        if len(self.dataframes) == 0:
            raise FakeDataFrameParserException(f'No dataframes were created')
        #print (f'References = {self.__reference_dict}')
    

    
@magics_class
class AutoMagics(Magics):
    @needs_local_scope
    @line_cell_magic
    def fakermaker(self, line, cell, local_ns=None):
        params = {}
        if len(line) > 0:
            params = self.__get_magic_params(line)
        if 'lang' in params:
            cls = FakeDataFrameBuilder(cell, params['lang'])
        else:
            cls = FakeDataFrameBuilder(cell)
        if 'seed' in params:
            cls.seed(int(params['seed']))
        cls.parse()
        for name, df in cls.dataframes.items():
            local_ns[name] = df
    
    def __get_magic_params(self, line):
        result = {}
        r = re.findall("([\w]+)=([\w]+)", line)
        for k,v in r:
            result[k] = v
        return result


def load_ipython_extension(ipython):
    ipython.register_magics(AutoMagics)
