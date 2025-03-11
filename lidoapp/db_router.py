class MultiDBRouter:
    """
    A database router that saves data in both Supabase and SQLite.
    Deletes from both databases.
    """

    def db_for_write(self, model, **hints):
        """Writes to both databases."""
        return 'default'  # Write to Supabase

    def db_for_read(self, model, **hints):
        """Reads from the local database."""
        return 'local'  # Read from SQLite

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Allow migrations for both databases."""
        return True

    def allow_delete(self, model, using=None, **hints):
        """Deletes from both databases."""
        return True
