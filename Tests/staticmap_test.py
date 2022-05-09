from staticmap import StaticMap, Line

m = StaticMap(200, 200, 80)

coordinates = [[12.422, 45.427], [13.749, 44.885]]
line_outline = Line(coordinates, 'white', 6)
line = Line(coordinates, '#D2322D', 4)

m.add_line(line_outline)
m.add_line(line)

image = m.render()
image.save('ferry.png')