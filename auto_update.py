import data_import_tools as dit
import database_tools as dbt

dit.update_data()
dbt.to_sql()