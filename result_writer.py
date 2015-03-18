import csv
import os

from collections import namedtuple

ResultFiles = namedtuple('ResultFiles', ['gnuplot', 'csv', 'spreadsheet'])

class ResultWriter(object):
    '''Utility class for writing output data from the tuning process.'''

    def __init__(self, data_files):
        self.data_files = data_files
        self.csv_file = None

    def __enter__(self):
        if self.data_files.csv:
            self.csv_file = open(self.data_files.csv, 'wb')
            self.csv_writer = csv.writer(self.csv_file, delimiter=',',
                quotechar='"', quoting=csv.QUOTE_MINIMAL)
            self.csv_writer.writerow(['num_gangs', 'vector_length', 'time',
                'stdev', 'error msg'])
        return self

    def _add_row_to_csv(self, test_result):
        row = [ '{0:.0f}'.format(test_result.point[0]),
                '{0:.0f}'.format(test_result.point[1]),
                test_result.average,
                test_result.stdev ]
        if test_result.error:
            row.append(test_result.error)
        self.csv_writer.writerow(row)

    def add(self, test_result):
        if self.csv_file:
            self._add_row_to_csv(test_result)

    def _write_gnuplot_output(self, search_result):
        with open(self.data_files.gnuplot + '.dat', 'w') as f:
            lastx = 0
            for point in sorted(search_result.tests, key=lambda pt: pt.coords):
                res = search_result.tests[point]
                if res.has_error:
                    continue
                if point[0] != lastx:
                    f.write('\n') # Blank line between successive x-values
                    lastx = point[0]
                f.write('{0:<6.0f} {1:<6.0f} {2} {3}\n'.format(
                    point[0], point[1], res.average, res.stdev))

        full_filename = self.data_files.gnuplot
        prefix, suffix = os.path.splitext(full_filename)
        with open(full_filename if suffix else prefix + '.gp', 'w') as f:
            fmt = """# Script for gnuplot 5.0
set term postscript eps enhanced color size 10, 21 "Times-Roman,24"
set output "{filename_prefix}.eps"
set multiplot layout 3,1

set title "All Points Tested - Optimal: {num_gangs:.0f} gangs, vector length {vector_length:.0f} - Resulting time {time} (stdev: {stdev})"
set xlabel "Num Gangs"
set ylabel "Vector Length"
set zlabel "Time" rotate
set label 1 "{time}" at {num_gangs}, {vector_length}, {time} left
set grid

splot '{filename_prefix}.dat' using 1:2:3 notitle with points pointtype 7

splot '{filename_prefix}.dat' using 1:2:3 notitle with linespoints

set pm3d border linetype -1 linewidth 0.5
set palette
set hidden3d
splot '{filename_prefix}.dat' using 1:2:3 notitle pal with pm3d
"""
            f.write(fmt.format(
                filename_prefix = prefix,
                num_gangs = search_result.optimal[0],
                vector_length = search_result.optimal[1],
                time = search_result.tests[search_result.optimal].average,
                stdev = search_result.tests[search_result.optimal].stdev))

    def _write_spreadsheet(self, res, reps):
        with open(self.data_files.spreadsheet, 'w') as f:
            fmt = """<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <!-- Microsoft Office 2004 XML Spreadsheet (SpreadsheetML) -->
 <ExcelWorkbook xmlns="urn:schemas-microsoft-com:office:excel">
  <WindowHeight>6700</WindowHeight>
  <WindowWidth>16700</WindowWidth>
  <WindowTopX>200</WindowTopX>
  <WindowTopY>200</WindowTopY>
  <ProtectStructure>False</ProtectStructure>
  <ProtectWindows>False</ProtectWindows>
 </ExcelWorkbook>
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal">
   <Alignment ss:Vertical="Bottom"/>
   <Borders/>
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#000000"/>
   <Interior/>
   <NumberFormat/>
   <Protection/>
  </Style>
  <Style ss:ID="s62">
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#000000"/>
  </Style>
  <Style ss:ID="s63">
   <Alignment ss:Horizontal="Left" ss:Vertical="Bottom"/>
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#000000"/>
  </Style>
  <Style ss:ID="s64">
   <Alignment ss:Horizontal="Right" ss:Vertical="Bottom"/>
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#000000"/>
   <NumberFormat ss:Format="#,##0.0000000"/>
  </Style>
  <Style ss:ID="s65">
   <Alignment ss:Horizontal="Center" ss:Vertical="Bottom"/>
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#000000"/>
  </Style>
  <Style ss:ID="s68">
   <Alignment ss:Horizontal="Center" ss:Vertical="Bottom"/>
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#000000"/>
   <NumberFormat ss:Format="0"/>
  </Style>
  <Style ss:ID="s69">
   <Alignment ss:Horizontal="Center" ss:Vertical="Bottom"/>
   <Font ss:FontName="Times New Roman" ss:Size="12" ss:Color="#333399" ss:Bold="1"/>
   <NumberFormat ss:Format="Fixed"/>
  </Style>
  <Style ss:ID="s70">
   <Alignment ss:Horizontal="Left" ss:Vertical="Center"/>
   <Font ss:Size="12" ss:Color="#000000" ss:Bold="1"/>
   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
   <NumberFormat ss:Format="@"/>
  </Style>
  <Style ss:ID="s71">
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
   <Font ss:Size="12" ss:Color="#000000" ss:Bold="1"/>
   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
   <NumberFormat ss:Format="@"/>
  </Style>
 </Styles>
 <Worksheet ss:Name="Autotune Results">
  <Table ss:ExpandedColumnCount="11" ss:ExpandedRowCount="2" x:FullColumns="1"
   x:FullRows="1" ss:StyleID="s62" ss:DefaultColumnWidth="65"
   ss:DefaultRowHeight="15">
   <Column ss:StyleID="s63" ss:AutoFitWidth="0" ss:Width="90"/>
   <Column ss:StyleID="s64" ss:AutoFitWidth="0" ss:Width="72" ss:Span="3"/>
   <Column ss:Index="6" ss:StyleID="s65" ss:AutoFitWidth="0" ss:Span="5"/>
   <Row ss:AutoFitHeight="0" ss:Height="18" ss:StyleID="s71">
    <Cell ss:StyleID="s70"><Data ss:Type="String">Kernel</Data></Cell>
    <Cell><Data ss:Type="String">Orig Time</Data></Cell>
    <Cell><Data ss:Type="String">Stdev</Data></Cell>
    <Cell><Data ss:Type="String">Tuned Time</Data></Cell>
    <Cell><Data ss:Type="String">Stdev</Data></Cell>
    <Cell><Data ss:Type="String"># Gangs</Data></Cell>
    <Cell><Data ss:Type="String">Vec Len</Data></Cell>
    <Cell><Data ss:Type="String"># Iterations</Data></Cell>
    <Cell><Data ss:Type="String">Samples</Data></Cell>
    <Cell><Data ss:Type="String">Speedup</Data></Cell>
    <Cell><Data ss:Type="String">Signif?</Data></Cell>
   </Row>
   <Row ss:AutoFitHeight="0">
    <Cell ss:Index="4"><Data ss:Type="Number">{tuned_time}</Data></Cell>
    <Cell><Data ss:Type="Number">{tuned_stdev}</Data></Cell>
    <Cell><Data ss:Type="Number">{num_gangs}</Data></Cell>
    <Cell><Data ss:Type="Number">{vector_length}</Data></Cell>
    <Cell><Data ss:Type="Number">{num_iterations}</Data></Cell>
    <Cell ss:StyleID="s68"><Data ss:Type="Number">{num_repetitions}</Data></Cell>
    <Cell ss:StyleID="s69" ss:Formula="=RC[-8]/RC[-6]"><Data ss:Type="Number"></Data></Cell>
    <Cell ss:StyleID="s69"
     ss:Formula="=IF(AND(((RC[-9]-RC[-7])-TINV(0.1,((((RC[-8]^2/RC[-2])+(RC[-6]^2/RC[-2]))^2)/(((1/(RC[-2]+1))*(RC[-8]^2/RC[-2])^2)+((1/(RC[-2]+1))*(RC[-6]^2/RC[-2])^2))-2))*(SQRT((RC[-8]^2/RC[-2])+(RC[-6]^2/RC[-2]))))&lt;=0, ((RC[-9]-RC[-7])+TINV(0.1,((((RC[-8]^2/RC[-2])+(RC[-6]^2/RC[-2]))^2)/(((1/(RC[-2]+1))*(RC[-8]^2/RC[-2])^2)+((1/(RC[-2]+1))*(RC[-6]^2/RC[-2])^2))-2))*(SQRT(((RC[-8]^2/RC[-2]))+(RC[-6]^2/RC[-2]))))&gt;=0),&quot;No&quot;,&quot;YES&quot;)"><Data
      ss:Type="String"></Data></Cell>
   </Row>
  </Table>
  <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
   <FreezePanes/>
   <FrozenNoSplit/>
   <SplitHorizontal>1</SplitHorizontal>
   <TopRowBottomPane>1</TopRowBottomPane>
   <ActivePane>2</ActivePane>
   <Panes>
    <Pane>
     <Number>3</Number>
    </Pane>
    <Pane>
     <Number>2</Number>
     <ActiveCol>1</ActiveCol>
    </Pane>
   </Panes>
   <ProtectObjects>False</ProtectObjects>
   <ProtectScenarios>False</ProtectScenarios>
  </WorksheetOptions>
 </Worksheet>
</Workbook>
"""
            f.write(fmt.format(
                tuned_time = res.tests[res.optimal].average,
                tuned_stdev = res.tests[res.optimal].stdev,
                num_gangs = res.optimal[0],
                vector_length = res.optimal[1],
                num_iterations = res.num_iterations,
                num_repetitions = reps))

    def write_result(self, search_result, reps):
        if self.data_files.gnuplot is not None:
            self._write_gnuplot_output(search_result)

        if self.data_files.spreadsheet is not None:
            self._write_spreadsheet(search_result, reps)

    def __exit__(self, type, value, traceback):
        if self.csv_file is not None:
            self.csv_file.close()
