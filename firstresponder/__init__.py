# TODO: see area advisor add a way for the search input to be passed through ai, so it finds the best matching first responder and google how to implement NORMAL NO-AI search


# from django.contrib.gis.geos import Point

# user_location = Point(lng, lat)
# # Find all responders covering this location
# active_responders = FirstResponder.objects.filter(service_areas__polygon__contains=user_location)


# from django.contrib.gis.geos import Point

# user_longitude = 7.5
# user_latitude = 5.2
# user_location = Point(user_longitude, user_latitude, srid=4326)

# # High-speed spatial lookup using the GiST index
# active_responders = FirstResponder.objects.filter(
#     service_areas__contains=user_location
# )


# Find Responders Overlapping a Disaster ZoneTo see which responders have coverage zones that intersect with an active emergency perimeter:
# from django.contrib.gis.geos import Polygon
# disaster_zone = Polygon(((7.0, 5.0), (7.1, 5.0), (7.1, 5.1), (7.0, 5.1), (7.0, 5.0)))

# overlapping_responders = FirstResponder.objects.filter(
#     service_areas__intersects=disaster_zone
# )
