#!/usr/bin/env python

def fake_data():
    catalog_with_items = {}
    catalog_with_items['Database'] = {
        'PostgreSQL' : 'PostgreSQL desc',
        'MySQL' : 'MySQL desc',
        'Oracle' : 'Oracle desc',
        'Microsoft SQL Server' : 'Microsoft SQL Server desc',
        'SQLite' : 'SQLite desc'
    }
    catalog_with_items['Sport'] = {
        'Football' : 'Football desc',
        'Basketball' : 'Basketball desc',
        'Table Tennis' : 'Table Tennis desc',
        'Badminton' : 'Badminton desc',
        'Volleyball' : 'Volleyball desc'
    }
    catalog_with_items['Soccer'] = {
        'Soccer Cleats' : 'The shoes',
        'Jersey' : 'The shirt'
    }
    catalog_with_items['Basketball'] = {
        'Bat' : 'The bat'
    }
    catalog_with_items['Frisbee'] = {
        'Snowboarding' : 'Best for any terrain and conditions'
    }

    return catalog_with_items