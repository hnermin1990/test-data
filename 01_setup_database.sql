/* =========================================================
   01 - Create the database and the medallion schemas
   (Notebook 01 runs this automatically; you can also run it
    in SSMS / Azure Data Studio / VS Code mssql extension)
   ========================================================= */

IF DB_ID('WeatherDB') IS NULL
    CREATE DATABASE WeatherDB;
GO

USE WeatherDB;
GO

IF SCHEMA_ID('bronze') IS NULL EXEC('CREATE SCHEMA bronze');   -- raw data, exactly as received
GO
IF SCHEMA_ID('silver') IS NULL EXEC('CREATE SCHEMA silver');   -- cleaned & typed data
GO
IF SCHEMA_ID('gold')   IS NULL EXEC('CREATE SCHEMA gold');     -- business tables for BI + ML results
GO
