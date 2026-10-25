USE MultiServiceDB;
GO

IF COL_LENGTH(N'dbo.Users', N'PasswordHash') IS NULL
    ALTER TABLE dbo.Users ADD PasswordHash NVARCHAR(256) NULL;
IF COL_LENGTH(N'dbo.Users', N'IsAdmin') IS NULL
    ALTER TABLE dbo.Users ADD IsAdmin BIT NOT NULL
        CONSTRAINT DF_Users_IsAdmin DEFAULT 0 WITH VALUES;

IF COL_LENGTH(N'dbo.Users', N'ApprovalStatus') IS NULL
BEGIN
    ALTER TABLE dbo.Users ADD ApprovalStatus VARCHAR(20) NOT NULL
        CONSTRAINT DF_Users_ApprovalStatus DEFAULT 'APPROVED' WITH VALUES;
END;

IF COL_LENGTH(N'dbo.Users', N'ApprovalNote') IS NULL
    ALTER TABLE dbo.Users ADD ApprovalNote NVARCHAR(500) NULL;

IF COL_LENGTH(N'dbo.Users', N'ApprovedAt') IS NULL
    ALTER TABLE dbo.Users ADD ApprovedAt DATETIME2(0) NULL;
IF COL_LENGTH(N'dbo.Users', N'State') IS NULL
    ALTER TABLE dbo.Users ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Users_State DEFAULT N'Bihar' WITH VALUES;
IF COL_LENGTH(N'dbo.Users', N'District') IS NULL
    ALTER TABLE dbo.Users ADD District NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Users_District DEFAULT N'Siwan' WITH VALUES;
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_Users_ApprovalStatus')
    ALTER TABLE dbo.Users ADD CONSTRAINT CK_Users_ApprovalStatus
        CHECK (ApprovalStatus IN ('PENDING', 'APPROVED', 'REJECTED'));
GO
UPDATE dbo.Users
SET IsAdmin = CASE WHEN Role = 'admin' THEN 1 ELSE 0 END
WHERE IsAdmin <> CASE WHEN Role = 'admin' THEN 1 ELSE 0 END;
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.Users')
      AND name = N'CK_Users_IsAdminMatchesRole'
)
    ALTER TABLE dbo.Users ADD CONSTRAINT CK_Users_IsAdminMatchesRole
        CHECK ((Role = 'admin' AND IsAdmin = 1) OR (Role <> 'admin' AND IsAdmin = 0));
GO

IF COL_LENGTH(N'dbo.Electronics', N'State') IS NULL
    ALTER TABLE dbo.Electronics ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Electronics_State DEFAULT N'Bihar' WITH VALUES;
GO

IF COL_LENGTH(N'dbo.Medicines', N'State') IS NULL
    ALTER TABLE dbo.Medicines ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Medicines_State DEFAULT N'Bihar' WITH VALUES;
GO

IF COL_LENGTH(N'dbo.Advocates', N'State') IS NULL
    ALTER TABLE dbo.Advocates ADD State NVARCHAR(80) NOT NULL
        CONSTRAINT DF_Advocates_State DEFAULT N'Bihar' WITH VALUES;
GO

IF OBJECT_ID(N'dbo.ActivityLogs', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ActivityLogs (
        ActivityID INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ActivityLogs PRIMARY KEY,
        ActorUserID INT NULL,
        Action NVARCHAR(80) NOT NULL,
        TargetType NVARCHAR(40) NOT NULL,
        TargetID INT NULL,
        Description NVARCHAR(500) NOT NULL,
        CreatedAt DATETIME2(0) NOT NULL CONSTRAINT DF_ActivityLogs_CreatedAt DEFAULT SYSdatetime(),
        CONSTRAINT FK_ActivityLogs_Users FOREIGN KEY (ActorUserID) REFERENCES dbo.Users(UserID)
    );
    CREATE INDEX IX_ActivityLogs_Action ON dbo.ActivityLogs(Action);
    CREATE INDEX IX_ActivityLogs_CreatedAt ON dbo.ActivityLogs(CreatedAt);
END;
GO

PRINT 'Registration approval and admin activity schema is ready.';
GO
