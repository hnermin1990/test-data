/* =========================================================
   04 - (Optional, recommended) a read-only login for Power BI
   Power BI then sees ONLY the gold layer - not bronze/silver.
   ========================================================= */

USE master;
GO
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'powerbi_reader')
    CREATE LOGIN powerbi_reader WITH PASSWORD = 'PowerBI_Read123!', CHECK_POLICY = ON;
GO

USE WeatherDB;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'powerbi_reader')
    CREATE USER powerbi_reader FOR LOGIN powerbi_reader;
GO

GRANT SELECT ON SCHEMA::gold TO powerbi_reader;   -- read gold only
GO
