"""Store courses with embedded rosters and schedules."""
def exercise(client, collection):
    courses = collection("courses", {
        "bsonType": "object",
        "required": ["title", "code", "instructor", "schedule"],
        "properties": {
            "title": {"bsonType": "string"}, "code": {"bsonType": "string"},
            "instructor": {"bsonType": "string"}, "schedule": {"bsonType": "object"},
        },
    })
    courses.insert_many([
        {"code": code, "title": title, "instructor": teacher,
         "schedule": {"days": [day], "time": "10:00", "room": room},
         "students": [{"id": student, "name": name, "grade": "A"}],
         "prerequisite_codes": prerequisites}
        for code, title, teacher, day, room, student, name, prerequisites in [
            ("CS101", "Programming", "Rao", "Monday", "A1", "S1", "Mira", []),
            ("CS401", "Databases", "Rao", "Monday", "B2", "S2", "Dev", ["CS101"]),
            ("CS402", "Networking", "Patel", "Tuesday", "C3", "S3", "Ira", ["CS101"]),
        ]
    ])
    monday = list(courses.find({"schedule.days": "Monday"}, {"_id": 0}).sort("code"))
    students = list(courses.aggregate([
        {"$match": {"instructor": "Rao"}}, {"$unwind": "$students"},
        {"$project": {"_id": 0, "code": 1, "student": "$students"}},
    ]))
    return {"passed": len(monday) == len(students) == 2, "monday_courses": monday,
            "students_taught_by_rao": students,
            "prerequisite_design": "Reference stable course codes to avoid duplicating titles and schedules."}
