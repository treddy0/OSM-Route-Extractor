import csv
import simplekml
import math
import simplekml
import argparse
import sys
import logging


def fixType(coords):
    """changes coords from string of tuple of floats to tuple of floats

    Args:
        coords (string): string representation of coordinates

    Returns:
        tuple of ints: coordinates in usable type
    """
    return tuple(float(num) for num in coords.replace('(', '').replace(')', '').split(', '))


def swapLL(coords):
    """swaps longitude and latitude

    Args:
        coords ((float, float)): tuple of floats

    Returns:
        (float, float): tuple of floats
    """
    (lon, lat) = coords
    return (lat, lon)


def estimateDist(coord1, coord2):
    """a not so good estimation of distance between to logitude latidude coordinates

    Args:
        coord1 ((float, float)): a coordinate
        coord2 ((float, float)): a coordinate

    Returns:
        float: a distance metric without units
    """
    (x1, y1) = coord1
    (x2, y2) = coord2
    return math.sqrt((1000*(x2-x1))**2 + (1000*(y2-y1))**2)


def addLines(row, kml, filtering):
    """adds route to kml

    Args:
        row (list of strings): csv row with coordinates for route
        kml (a simpleKML object): kml object to be added to
    """
    # swap latitude and longitude for KML
    previous_Coord = swapLL(fixType(row[0]))
    # keep track of avergae distance between nodes for filtering
    averageD = 0
    if filtering:
        for current_Coord in row[1:]:
            current_Coord = swapLL(fixType(current_Coord))
            averageD += estimateDist(current_Coord, previous_Coord)
            previous_Coord = current_Coord
    # if filtering check if average distance between nodes is low enough
    if averageD/(len(row)-1) < 2:
        previous_Coord = swapLL(fixType(row[0]))
        for current_Coord in row[1:]:
            current_Coord = swapLL(fixType(current_Coord))
            # some routes link the begining and end ways or have large gaps
            # this avoids drawing lines between those
            if estimateDist(current_Coord, previous_Coord) < 20:
                linestring = kml.newlinestring()

                linestring.coords = [previous_Coord, current_Coord]
            previous_Coord = current_Coord
        return 1
    return 0


def main(args):

    kml = simplekml.Kml(open=1)
    try:
        file = open(args.in_path, newline='')
    except:
        logging.error("could not open file")
        sys.exit()

    reader = csv.reader(file, delimiter=' ', quotechar='|')
    count = 0
    for row in reader:
        if count < args.number:
            count += addLines(row, kml, args.filtering)

    try:
        kml.save(args.out_path)
    except:
        logging.error("could not save to " + args.out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("in_path", help="path to input file (csv)")
    parser.add_argument("out_path", help="path to output file (kml)")
    parser.add_argument("-f", "--filtering", action="store_true",
                        help="filter out poorly mapped routes")
    parser.add_argument("-n", "--number", action="store", type=int, default=20,
                        help="number of routes to output")

    args = parser.parse_args()
    main(args)
