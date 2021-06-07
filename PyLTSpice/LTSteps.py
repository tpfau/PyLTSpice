#!/usr/bin/env python
# coding=utf-8

# -------------------------------------------------------------------------------
# Name:        LTSteps.py
# Purpose:     Process LTSpice output files and align data for usage in a spread-
#              sheet tool such as Excel, or Calc.
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     19-05-2014
# Licence:     Free
# Version:     0.3  Transforming the procedure into a callable one in order
#              to call them from a higher level script.
# -------------------------------------------------------------------------------

"""
This module allows to process data generated by LTSpice during simulation. There are three types of files that are
handled by this module.

    + log files - Files with the extension '.log' that are automatically generated during simulation, and that are
        normally accessible with the shortcut Ctrl+L after a simulation is ran.
        Log files are interesting for two reasons.

            1. If .STEP primitives are used, the log file contain the correspondence between the step run and the step
            value configuration.

            2. If .MEAS primitives are used in the schematic, the log file contains the measurements made on the output
            data.

        LTSteps.py can be used to retrieve both step and measurement information from log files.

    + txt files - Files exported from the Plot File -> Export data as text menu. This file is an text file where data is
      saved in the text format. The reason to use PyLTSpice instead of another popular lib as pandas, is because the data
      format when .STEPS are used in the simulation is not not very practical. The PyLTSpice LTSteps.py can be used to
      reformat the text, so that the run parameter is added to the data as an additional column instead of a table
      divider. Please Check LTSpiceExport class for more information.

    + mout files - Files generated by the Plot File -> Execute .MEAS Script menu. This command allows the user to run
      predefined .MEAS commands and which creates a .mout file. A mout file has the measurement information stored in the
      following format:

      .. code-block:: text

            Measurement: Vout_rms
            step	RMS(V(OUT))	FROM	TO
             1	1.41109	0	0.001
             2	1.40729	0	0.001

            Measurement: Vin_rms
              step	RMS(V(IN))	FROM	TO
                 1	0.706221	0	0.001
                 2	0.704738	0	0.001

            Measurement: gain
              step	Vout_rms/Vin_rms
                 1	1.99809
                 2	1.99689


The LTSteps.py can be used directly from a command line by invoking python with the -m option as exemplified below.

.. code-block:: text

    $ python -m PyLTSpice.LTSteps <path_to_filename>

If <path_to_filename> is a log file, it will create a file with the same name, but with extension .tout that is a
tab separated value (tsv) file, which contains the .STEP and .MEAS information collected.

If <path_to_filename> is a txt exported file, it will create a file with the same name, but with extension .tsv a
tab separated value (tsv) file, which contains data reformatted with the step number as one of the columns. Please
consult the reformat_LTSpice_export() function for more information.

If <path_to_filename> is a mout file, it will create a file with the same name, but with extension .tmout that is a
tab separated value (tsv) file, which contains the .MEAS information collected, but adding the STEP run information
as one of the columns.

If <path_to_filename> argument is ommited, the script will automatically search for the newest .log/.txt/.mout file
and use it.

"""
__author__ = "Nuno Canto Brum <me@nunobrum.com>"
__copyright__ = "Copyright 2017, Fribourg Switzerland"

import re
import os
import sys
from collections import OrderedDict
from typing import Union, Iterable, List

if __name__ == "__main__":
    def message(*strs):
        for string in strs:
            print(string)
else:
    def message(*strs):
        pass


def enc_norm(line):
    if len(line) > 1 and line[0] == '\0':  # This is to decode the LTSpice XVII encoding (unable to find the exact code)
        return line[1::2]  # Removes zeros from the encoding
    else:
        return line  # Return as is


def try_convert_value(value: str) -> Union[int, float, str]:
    """
    Tries to convert the string into an integer and if fails, tries to convert to a float, if it fails, then returns the
    value as string.

    :param value: value to convert
    :type value: str
    :return: converted value, if applicable
    :rtype: int, float, str
    """
    try:
        ans = int(value)
    except ValueError:
        try:
            ans = float(value)
        except ValueError:
            ans = value
    return ans


def try_convert_values(values: Iterable[str]) -> List[str]:
    """
    Same as try_convert_values but applicable to an iterable

    :param values: Iterable that returns strings
    :type values:
    :return: list with the values converted to either integer (int) or floating point (float)
    :rtype: List[str]
    """
    answer = []
    for value in values:
        answer.append(try_convert_value(value))
    return answer


def reformat_LTSpice_export(export_file: str, tabular_file: str):
    """
    Reads an LTSpice File Export file and writes it back in a format that is more convenient for data treatment.

    When using the "Export data as text" in the raw file menu the data is already exported in a tabular format.
    However, if steps are being used, the step information doesn't appear on the table.  Instead the successive STEP
    runs are stacked on one after another, separated by the following text:

    .. code-block:: text

        Step Information: Ton=400m  (Run: 2/2)

    What would be desirable would be that the step number (Run number) and the STEP variable would be placed within the
    columns.  This allows for example using Excel functionality known as Pivot Tables to filter out data, or some other
    database selection function.
    The tab is chosen as separator because it is normally compatible with pasting data into Excel.

    :param export_file: Filename of the .txt file generated by the "Export Data as Text"
    :type export_file: str
    :param tabular_file: Filename of the tab separated values (TSV) file that
    :type tabular_file: str
    :return: Nothing
    :rtype: None

    """
    fin = open(export_file, 'r')
    fout = open(tabular_file, 'w')

    headers = enc_norm(fin.readline())
    # writing header
    go_header = True
    run_no = 0  # Just to avoid warning, this is later overridden by the step information
    param_values = ""  # Just to avoid warning, this is later overridden by the step information
    regx = re.compile(r"Step Information: ([\w=\d\. -]+) +\(Run: (\d*)/\d*\)\n")
    for line in fin:
        line = enc_norm(line)
        if line.startswith("Step Information:"):
            match = regx.match(line)
            # message(line, end="")
            if match:
                # message(match.groups())
                step, run_no = match.groups()
                # message(step, line, end="")
                params = []
                for param in step.split():
                    params.append(param.split('=')[1])
                param_values = "\t".join(params)

                if go_header:
                    header_keys = []
                    for param in step.split():
                        header_keys.append(param.split('=')[0])
                    param_header = "\t".join(header_keys)
                    fout.write("Run\t%s\t%s" % (param_header, headers))
                    message("Run\t%s\t%s" % (param_header, headers))
                    go_header = False
                    # message("%s\t%s"% (run_no, param_values))
        else:
            fout.write("%s\t%s\t%s" % (run_no, param_values, line))

    fin.close()
    fout.close()


class LTSpiceExport(object):
    """
    Opens and reads LTSpice export data when using the "Export data as text" in the File Menu on the waveform window.

    The data is then accessible by using the following attributes implemented in this class.

    :property headers: list containing the headers on the exported data
    :property dataset: dictionary in which the keys are the the headers and the export file and the values are
        lists. When reading STEPed data, a new kew called 'runno' is added to the dataset.

    **Examples**

    ::

        export_data = LTSpiceExport("export_data_file.txt")
        for value in export_data.dataset['I(V1)']:
            print(f"Do something with this value {value}")

    :param export_filename: path to the Export file.
    :type export_filename: str
    """

    def __init__(self, export_filename: str):
        fin = open(export_filename, 'r')
        file_header = enc_norm(fin.readline())

        self.headers = file_header.split('\t')
        # Set to read header
        go_header = True

        curr_dic = {}
        self.dataset = {}

        regx = re.compile(r"Step Information: ([\w=\d\. -]+) +\(Run: (\d*)/\d*\)\n")
        for line in fin:
            line = enc_norm(line)
            if line.startswith("Step Information:"):
                match = regx.match(line)
                # message(line, end="")
                if match:
                    # message(match.groups())
                    step, run_no = match.groups()
                    # message(step, line, end="")
                    curr_dic['runno'] = run_no
                    for param in step.split():
                        key, value = param.split('=')
                        curr_dic[key] = try_convert_value(value)

                    if go_header:
                        go_header = False  # This is executed only once
                        for key in self.headers:
                            self.dataset[key] = []  # Initializes an empty list

                        for key in curr_dic:
                            self.dataset[key] = []  # Initializes an empty list

            else:
                values = line.split('\t')

                for key in curr_dic:
                    self.dataset[key].append(curr_dic[key])

                for i in range(len(values)):
                    self.dataset[self.headers[i]].append(try_convert_value(values[i]))

        fin.close()


class LTSpiceLogReader(object):
    """
    Reads an LTSpice log file and retrieves the step information if it exists. The step information is then accessible
    by using the 'stepset' property of this class.
    This class is intended to be used together with the LTSpice_RawRead to retrieve the runs that are associated with a
    given parameter setting.

    This class constructor only reads the step information of the log file. If the measures are needed, then the user
    should call the get_measures() method.

    :property stepset: dictionary in which the keys are the variables that were STEP'ed during the simulation and
        the associated value is a list representing the sequence of assigned values during simulation.

    :property headers: list containing the headers on the exported data. This is only populated when the *read_measures*
        optional parameter is set to False.

    :property dataset: dictionary in which the keys are the the headers and the export file and the values are
         lists. This is information is only populated when the *read_measures* optional parameter is set to False.

    :param log_filename: path to the Export file.
    :type log_filename: str
    :param read_measures: Optional parameter to skip measuring data reading.
    :type read_measures: boolean
    """

    def __init__(self, log_filename: str, read_measures=True):
        self.logname = log_filename
        fin = open(log_filename, 'r')
        self.step_count = 0
        self.stepset = {}
        self.dataset = OrderedDict()  # Dictionary in which the order of the keys is kept
        self.measure_count = 0

        # Preparing a stepless measurement read regular expression
        regx = re.compile(
                r"^(?P<name>\w+):\s+.*=(?P<value>[\d\.E+\-\(\)dB,°]+)(( FROM (?P<from>[\d\.E+-]*) TO (?P<to>[\d\.E+-]*))|( at (?P<at>[\d\.E+-]*)))?",
                re.IGNORECASE)

        message("Processing LOG file", log_filename)

        line = enc_norm(fin.readline())

        while line:
            if line.startswith(".step"):
                # message(line)
                self.step_count += 1
                tokens = line.strip('\n').split(' ')
                for tok in tokens[1:]:
                    lhs, rhs = tok.split("=")
                    # Try to convert to int or float
                    rhs = try_convert_value(rhs)

                    ll = self.stepset.get(lhs, None)
                    if ll:
                        ll.append(rhs)
                    else:
                        self.stepset[lhs] = [rhs]

            elif line.startswith("Measurement:"):
                if not read_measures:
                    fin.close()
                    return
                else:
                    break  # Jumps to the section that reads measurements

            if self.step_count == 0:  # then there are no steps,
                # there are only measures taken in the format parameter: measurement
                # A few examples of readings
                # vout_rms: RMS(v(out))=1.41109 FROM 0 TO 0.001  => Interval
                # vin_rms: RMS(v(in))=0.70622 FROM 0 TO 0.001  => Interval
                # gain: vout_rms/vin_rms=1.99809 => Parameter
                # vout1m: v(out)=-0.0186257 at 0.001 => Point
                match = regx.match(line)
                if match:
                    # Get the data
                    dataname = match.group('name')
                    if match.group('from'):
                        headers = [dataname, dataname + "_FROM", dataname + "_TO"]
                        measurements = [match.group('value'), match.group('from'), match.group('to')]
                    elif match.group('at'):
                        headers = [dataname, dataname + "_at"]
                        measurements = [match.group('value'), match.group('at')]
                    else:
                        headers = [dataname]
                        measurements = [match.group('value')]

                    for k, title in enumerate(headers):
                        self.dataset[title] = [
                            try_convert_value(measurements[k])]  # need to be a list for compatibility
            line = enc_norm(fin.readline())

        # message("Reading Measurements")
        dataname = None

        headers = []  # Initializing an empty parameters
        measurements = []
        while line:
            line = line.strip('\n')
            if line.startswith("Measurement: "):
                if dataname:  # If previous measurement was saved
                    # store the info
                    if len(measurements):
                        message("Storing Measurement %s (count %d)" % (dataname, len(measurements)))
                        for k, title in enumerate(headers):
                            self.dataset[title] = [line[k] for line in measurements]
                    headers = []
                    measurements = []
                dataname = line[13:]  # text which is after "Measurement: ". len("Measurement: ") -> 13
                message("Reading Measurement %s" % line[13:])
            else:
                tokens = line.split("\t")
                if len(tokens) >= 2:
                    try:
                        int(tokens[0])  # This instruction only serves to trigger the exception
                        meas = tokens[1:]  # [float(x) for x in tokens[1:]]
                        measurements.append(try_convert_values(meas))
                        self.measure_count += 1
                    except ValueError:
                        if len(tokens) >= 3 and (tokens[2] == "FROM" or tokens[2] == 'at'):
                            tokens[2] = dataname + '_' + tokens[2]
                        if len(tokens) >= 4 and tokens[3] == "TO":
                            tokens[3] = dataname + "_TO"
                        headers = [dataname] + tokens[2:]
                        measurements = []
                else:
                    message("->", line)

            line = enc_norm(fin.readline())  # advance to the next line

        # storing the last data into the dataset
        message("Storing Measurement %s" % dataname)
        if len(measurements):
            for k, title in enumerate(headers):
                self.dataset[title] = [line[k] for line in measurements]

        message("%d measurements" % len(self.dataset))
        message("Identified %d steps, read %d measurements" % (self.step_count, self.measure_count))

        fin.close()

    def steps_with_parameter_equal_to(self, param: str, value: Union[str, int, float]) -> List[int]:
        """
        Returns the steps that contain a given condition.

        :param param: parameter identifier on LTSpice simulation
        :type param: str
        :param value:
        :type value:
        :return: List of positions that respect the condition of equality with parameter value
        :rtype: List[int]
        """
        condition_set = self.stepset[param]
        # tries to convert the value to integer or float, for consistency with data loading implemetation
        v = try_convert_value(value)
        # returns the positions where there is match
        return [i for i, a in enumerate(condition_set) if a == v]

    def steps_with_conditions(self, **conditions) -> List[int]:
        """
        Returns the steps that respect one more more equality conditions

        :key conditions: parameters within the LTSpice simulation. Values are the matches to be found.
        :return: List of steps that repect all the given conditions
        :rtype: List[int]
        """
        current_set = None
        for param, value in conditions.items():
            condition_set = self.steps_with_parameter_equal_to(param, value)
            if current_set is None:
                # initialises the list
                current_set = condition_set
            else:
                # makes the intersection between the lists
                current_set = [v for v in current_set if v in condition_set]
        return current_set

    def get_measure_names(self):
        self.dataset.keys()

    def get_measure_value(self, measure, step: int = None):
        if step is None:
            if len(self.dataset[measure]) == 1:
                return self.dataset[measure][0]
            else:
                raise IndexError("In stepped data, the step number needs to be provided")
        else:
            return self.dataset[measure][step]

    def get_measure_values_at_steps(self, measure, steps):
        if steps is None:
            return self.dataset[measure]  # Returns everything
        elif isinstance(steps, int):
            return self.dataset[measure][steps]
        else:  # Assuming it is an iterable
            return [self.dataset[measure][step] for step in steps]

    def export_data(self, export_file: str, append_with_line_prefix=None):
        """
        Exports the measurement information to a tab separated value (.tsv) format. If step data is found, it is
        included in the exported file.

        When using export data together with LTSpiceBatch.py classes, it may be helpful to append data to an existing
        file. For this purpose, the user can user the append_with_line_prefix argument to indicate that an append should
        be done. And in this case, the user must provide a string that will identify the LTSpice batch run.

        :param export_file: path to the file containing the information
        :type export_file: str
        :param append_with_line_prefix: user information to be written in the file in case an append is to be made.
        :type append_with_line_prefix: str
        :return: Nothing
        """
        # message(tokens)
        if append_with_line_prefix is None:
            mode = 'w'  # rewrites the file
        else:
            mode = 'a'  # Appends an existing file

        if len(self.dataset) == 0:
            print("Empty data set. Exiting without writing file.")
            return

        fout = open(export_file, mode)

        if append_with_line_prefix is not None:  # if an append it will write the filename first
            fout.write('user info\t')

        fout.write("step\t%s\t%s\n" % ("\t".join(self.stepset.keys()), "\t".join(self.dataset)))
        first_parameter = next(iter(self.dataset))
        for index in range(len(self.dataset[first_parameter])):
            if self.step_count == 0:
                step_data = []  # Empty step
            else:
                step_data = [self.stepset[param][index] for param in self.stepset.keys()]
            meas_data = [self.dataset[param][index] for param in self.dataset]

            if append_with_line_prefix is not None:  # if an append it will write the filename first
                fout.write(append_with_line_prefix + '\t')
            fout.write("%d" % (index + 1))
            for s in step_data:
                fout.write(f'\t{s}')

            for tok in meas_data:
                if isinstance(tok, list):
                    for x in tok:
                        fout.write(f'\t{x}')
                else:
                    fout.write(f'\t{tok}')
            fout.write('\n')

        fout.close()


if __name__ == "__main__":

    def valid_extension(filename):
        return filename.endswith('.txt') or filename.endswith('.log') or filename.endswith('.mout')


    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if not valid_extension(filename):
            print("Invalid extension in filename '%s'" % filename)
            print("This tool only supports the following extensions :'.txt','.log','.mout'")
            exit(-1)
    else:
        filename = None
        newer_date = 0
        for f in os.listdir():
            date = os.path.getmtime(f)
            if date > newer_date and valid_extension(f):
                newer_date = date
                filename = f
    if filename is None:
        print("File not found")
        print("This tool only supports the following extensions :'.txt','.log','.mout'")
        exit(-1)

    fname_out = None
    if filename.endswith('.txt'):
        fname_out = filename.rstrip('txt') + 'tsv'
    elif filename.endswith('.log'):
        fname_out = filename.rstrip('log') + 'tlog'
    elif filename.endswith('.mout'):
        fname_out = filename.rstrip('mout') + 'tmout'
    else:
        print("Error in file type")
        print("This tool only supports the following extensions :'.txt','.log','.mout'")
        exit(-1)

    if fname_out is not None:
        print("Processing File %s" % filename)
        print("Creating File %s" % fname_out)
        if filename.endswith('txt'):
            print("Processing Data File")
            reformat_LTSpice_export(filename, fname_out)
        elif filename.endswith("log"):
            data = LTSpiceLogReader(filename)
            data.export_data(fname_out)
        elif filename.endswith(".mout"):
            data = LTSpiceLogReader(filename.rstrip('mout') + 'log')
            data.export_data(fname_out)

    # input("Press Enter to Continue")
