#!/usr/bin/env python3
"""
Migration script to add layout_style column to quizzes table
"""

from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('quizzes')]
            
            if 'layout_style' in columns:
                print("✓ Column 'layout_style' already exists in quizzes table")
                return
            
            # Add the column
            with db.engine.connect() as connection:
                connection.execute(text(
                    "ALTER TABLE quizzes ADD COLUMN layout_style VARCHAR(20) DEFAULT 'grid'"
                ))
                connection.commit()
            
            print("✓ Successfully added 'layout_style' column to quizzes table")
            print("  All existing quizzes now default to 'grid' layout")
            
        except Exception as e:
            print(f"✗ Error during migration: {e}")
            raise

if __name__ == '__main__':
    migrate()
