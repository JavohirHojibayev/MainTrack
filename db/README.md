# MineTrack DB

## Backup

```powershell
pg_dump -h 127.0.0.1 -p 5432 -U minetrack_user -d minetrack_db -F c -f minetrack_db.backup
```

## Restore

```powershell
pg_restore -h 127.0.0.1 -p 5432 -U minetrack_user -d minetrack_db -c minetrack_db.backup
```
