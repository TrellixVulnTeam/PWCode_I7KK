#! python3

import sys
import csv
import sqlite3
csv.field_size_limit(sys.maxsize)


def chunks(data, rows=10000):
    for i in range(0, len(data), rows):
        yield data[i:i+rows]


def main():
    table = sys.argv[1]  # table name s first argument
    tsv_file = sys.argv[2]  # data file as secong argument
    con = sqlite3.connect(sys.argv[3])  # database file path as third argument
    cur = con.cursor()

    with open(tsv_file, 'r') as f:
        reader = csv.reader(f, delimiter='\t', skipinitialspace=True, quoting=csv.QUOTE_NONE, quotechar='', escapechar='')
        header = next(reader)
        columns = ','.join(header)  # Skip header, get column names
        values = ','.join(['?' for x in header])  # Dummy values

        lines = [row for row in reader]
        data = chunks(lines)  # divide into 10000 rows each

        for chunk in data:
            cur.execute('BEGIN TRANSACTION')

            for line in chunk:
                cur.execute('INSERT INTO ' + table + ' (' + columns + ') VALUES(' + values + ');', line)

            cur.execute('COMMIT')

    print(table + ' imported successfully')


if __name__ == '__main__':
    main()
