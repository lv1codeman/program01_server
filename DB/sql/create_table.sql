CREATE TABLE "categories" (
	"category_id"	INTEGER NOT NULL,
	"category_name"	TEXT NOT NULL,
	PRIMARY KEY("category_id" AUTOINCREMENT)
);

CREATE TABLE "categories" (
	"category_id"	INTEGER NOT NULL,
	"category_name"	TEXT NOT NULL,
	PRIMARY KEY("category_id" AUTOINCREMENT)
);

CREATE TABLE "domains" (
	"domain_id"	INTEGER NOT NULL,
	"domain_name"	TEXT NOT NULL,
	PRIMARY KEY("domain_id" AUTOINCREMENT)
);

CREATE TABLE "subjects" (
	"subject_id"	INTEGER NOT NULL,
	"subject_unit"	TEXT NOT NULL,
	"subject_sub_id"	TEXT NOT NULL,
	"subject_sys"	TEXT NOT NULL,
	"subject_name"	TEXT NOT NULL,
	"subject_eng_name"	TEXT,
	"subject_credit"	INTEGER NOT NULL,
	"subject_hour"	INTEGER NOT NULL,
	PRIMARY KEY("subject_id" AUTOINCREMENT)
);

CREATE TABLE "scores" (
	"score_id"	INTEGER NOT NULL,
	"student_id"	TEXT NOT NULL,
	"subject_sub_id"	TEXT NOT NULL,
	"score"	INTEGER,
	"score_year"	INTEGER,
	"score_semester"	INTEGER,
	PRIMARY KEY("score_id" AUTOINCREMENT)
);

CREATE TABLE "program_structure" (
	"program_structure_id"	INTEGER NOT NULL,
	"program_id"	INTEGER NOT NULL,
	"category_id"	INTEGER NOT NULL,
	"domain_id"	INTEGER NOT NULL DEFAULT NULL,
	"subject_sub_id"	TEXT NOT NULL,
	UNIQUE("subject_sub_id","domain_id"),
	UNIQUE("subject_sub_id","category_id"),
	PRIMARY KEY("program_structure_id"),
	FOREIGN KEY("program_id") REFERENCES "programs"("program_id") ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY("subject_sub_id") REFERENCES "subjects"("subject_id"),
	FOREIGN KEY("category_id") REFERENCES "categories"("category_id") ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY("domain_id") REFERENCES "domains"("domain_id") ON DELETE CASCADE ON UPDATE CASCADE
);