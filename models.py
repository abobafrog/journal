from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Student(Base):
    tablename = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    marks = relationship("Mark", back_populates="student")

class Lesson(Base):
    tablename = "lessons"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    topic = Column(String)
    marks = relationship("Mark", back_populates="lesson")

class Mark(Base):
    tablename = "marks"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    present = Column(Boolean, default=False)
    note = Column(String)

    student = relationship("Student", back_populates="marks")
    lesson = relationship("Lesson", back_populates="marks")
