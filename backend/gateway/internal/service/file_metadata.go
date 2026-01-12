package service

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type StoredFile struct {
	ID         uuid.UUID
	UserID     uuid.UUID
	FileName   string
	MimeType   string
	FileSize   int64
	Bucket     string
	ObjectKey  string
	Status     string
	Visibility string
	CreatedAt  time.Time
	UpdatedAt  time.Time
	DeletedAt  *time.Time
}

type FileMetadataService struct {
	pool *pgxpool.Pool
}

func NewFileMetadataService(pool *pgxpool.Pool) *FileMetadataService {
	return &FileMetadataService{pool: pool}
}

func (s *FileMetadataService) CreatePendingFile(
	ctx context.Context,
	fileID uuid.UUID,
	userID uuid.UUID,
	fileName string,
	mimeType string,
	fileSize int64,
	bucket string,
	objectKey string,
) (StoredFile, error) {
	row := s.pool.QueryRow(ctx, `
		INSERT INTO stored_files (
			id, user_id, file_name, mime_type, file_size, bucket, object_key, status, visibility
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, 'uploading', 'private'
		)
		RETURNING id, user_id, file_name, mime_type, file_size, bucket, object_key,
			status, visibility, created_at, updated_at, deleted_at
	`, fileID, userID, fileName, mimeType, fileSize, bucket, objectKey)

	return scanStoredFile(row)
}

func (s *FileMetadataService) UpdateFileStatus(
	ctx context.Context,
	fileID uuid.UUID,
	userID uuid.UUID,
	status string,
	visibility string,
) (StoredFile, error) {
	row := s.pool.QueryRow(ctx, `
		UPDATE stored_files
		SET status = $1,
			visibility = $2,
			updated_at = NOW()
		WHERE id = $3
			AND user_id = $4
			AND deleted_at IS NULL
		RETURNING id, user_id, file_name, mime_type, file_size, bucket, object_key,
			status, visibility, created_at, updated_at, deleted_at
	`, status, visibility, fileID, userID)

	return scanStoredFile(row)
}

func (s *FileMetadataService) GetFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID) (StoredFile, error) {
	row := s.pool.QueryRow(ctx, `
		SELECT id, user_id, file_name, mime_type, file_size, bucket, object_key,
			status, visibility, created_at, updated_at, deleted_at
		FROM stored_files
		WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
	`, fileID, userID)

	return scanStoredFile(row)
}

func (s *FileMetadataService) GetFileForGroupView(
	ctx context.Context,
	fileID uuid.UUID,
	groupID uuid.UUID,
	userID uuid.UUID,
) (StoredFile, error) {
	row := s.pool.QueryRow(ctx, `
		SELECT sf.id, sf.user_id, sf.file_name, sf.mime_type, sf.file_size, sf.bucket, sf.object_key,
			sf.status, sf.visibility, sf.created_at, sf.updated_at, sf.deleted_at
		FROM stored_files sf
		JOIN group_files gf ON gf.file_id = sf.id AND gf.deleted_at IS NULL
		JOIN group_members gm ON gm.group_id = gf.group_id AND gm.user_id = $3 AND gm.deleted_at IS NULL
		WHERE sf.id = $1 AND gf.group_id = $2 AND sf.deleted_at IS NULL
			AND (
				gm.role = 'OWNER'
				OR (gm.role = 'ADMIN' AND gf.view_role IN ('ADMIN', 'MEMBER'))
				OR (gm.role = 'MEMBER' AND gf.view_role = 'MEMBER')
			)
	`, fileID, groupID, userID)

	return scanStoredFile(row)
}

func (s *FileMetadataService) GetFileForGroupDownload(
	ctx context.Context,
	fileID uuid.UUID,
	groupID uuid.UUID,
	userID uuid.UUID,
) (StoredFile, error) {
	row := s.pool.QueryRow(ctx, `
		SELECT sf.id, sf.user_id, sf.file_name, sf.mime_type, sf.file_size, sf.bucket, sf.object_key,
			sf.status, sf.visibility, sf.created_at, sf.updated_at, sf.deleted_at
		FROM stored_files sf
		JOIN group_files gf ON gf.file_id = sf.id AND gf.deleted_at IS NULL
		JOIN group_members gm ON gm.group_id = gf.group_id AND gm.user_id = $3 AND gm.deleted_at IS NULL
		WHERE sf.id = $1 AND gf.group_id = $2 AND sf.deleted_at IS NULL
			AND (
				gm.role = 'OWNER'
				OR (gm.role = 'ADMIN' AND gf.download_role IN ('ADMIN', 'MEMBER'))
				OR (gm.role = 'MEMBER' AND gf.download_role = 'MEMBER')
			)
	`, fileID, groupID, userID)

	return scanStoredFile(row)
}

func (s *FileMetadataService) ListFiles(
	ctx context.Context,
	userID uuid.UUID,
	status string,
	limit int,
	offset int,
) ([]StoredFile, error) {
	limitVal := limit
	if limitVal <= 0 {
		limitVal = 20
	}
	offsetVal := offset
	if offsetVal < 0 {
		offsetVal = 0
	}

	var rows pgx.Rows
	var err error
	if status == "" {
		rows, err = s.pool.Query(ctx, `
			SELECT id, user_id, file_name, mime_type, file_size, bucket, object_key,
				status, visibility, created_at, updated_at, deleted_at
			FROM stored_files
			WHERE user_id = $1 AND deleted_at IS NULL
			ORDER BY created_at DESC
			LIMIT $2 OFFSET $3
		`, userID, limitVal, offsetVal)
	} else {
		rows, err = s.pool.Query(ctx, `
			SELECT id, user_id, file_name, mime_type, file_size, bucket, object_key,
				status, visibility, created_at, updated_at, deleted_at
			FROM stored_files
			WHERE user_id = $1 AND status = $2 AND deleted_at IS NULL
			ORDER BY created_at DESC
			LIMIT $3 OFFSET $4
		`, userID, status, limitVal, offsetVal)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	files := make([]StoredFile, 0)
	for rows.Next() {
		file, scanErr := scanStoredFile(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		files = append(files, file)
	}
	return files, rows.Err()
}

func (s *FileMetadataService) SearchFiles(
	ctx context.Context,
	userID uuid.UUID,
	query string,
	limit int,
) ([]StoredFile, error) {
	limitVal := limit
	if limitVal <= 0 {
		limitVal = 20
	}
	searchTerm := "%" + query + "%"

	rows, err := s.pool.Query(ctx, `
		SELECT id, user_id, file_name, mime_type, file_size, bucket, object_key,
			status, visibility, created_at, updated_at, deleted_at
		FROM stored_files
		WHERE user_id = $1
			AND deleted_at IS NULL
			AND (file_name ILIKE $2 OR mime_type ILIKE $2)
		ORDER BY created_at DESC
		LIMIT $3
	`, userID, searchTerm, limitVal)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	files := make([]StoredFile, 0)
	for rows.Next() {
		file, scanErr := scanStoredFile(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		files = append(files, file)
	}
	return files, rows.Err()
}

func (s *FileMetadataService) SoftDeleteFile(ctx context.Context, fileID uuid.UUID, userID uuid.UUID) (StoredFile, error) {
	row := s.pool.QueryRow(ctx, `
		UPDATE stored_files
		SET deleted_at = NOW(),
			status = 'deleted',
			updated_at = NOW()
		WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
		RETURNING id, user_id, file_name, mime_type, file_size, bucket, object_key,
			status, visibility, created_at, updated_at, deleted_at
	`, fileID, userID)

	return scanStoredFile(row)
}

func (s *FileMetadataService) ListStaleFiles(ctx context.Context, cutoff time.Time, limit int) ([]StoredFile, error) {
	limitVal := limit
	if limitVal <= 0 {
		limitVal = 200
	}

	rows, err := s.pool.Query(ctx, `
		SELECT id, user_id, file_name, mime_type, file_size, bucket, object_key,
			status, visibility, created_at, updated_at, deleted_at
		FROM stored_files
		WHERE (
			status IN ('uploading', 'failed') AND created_at < $1
		) OR (
			deleted_at IS NOT NULL AND deleted_at < $1
		)
		ORDER BY created_at ASC
		LIMIT $2
	`, cutoff, limitVal)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	files := make([]StoredFile, 0)
	for rows.Next() {
		file, scanErr := scanStoredFile(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		files = append(files, file)
	}
	return files, rows.Err()
}

func (s *FileMetadataService) HardDeleteFile(ctx context.Context, fileID uuid.UUID) error {
	_, err := s.pool.Exec(ctx, `DELETE FROM stored_files WHERE id = $1`, fileID)
	return err
}

func scanStoredFile(row pgx.Row) (StoredFile, error) {
	var file StoredFile
	err := row.Scan(
		&file.ID,
		&file.UserID,
		&file.FileName,
		&file.MimeType,
		&file.FileSize,
		&file.Bucket,
		&file.ObjectKey,
		&file.Status,
		&file.Visibility,
		&file.CreatedAt,
		&file.UpdatedAt,
		&file.DeletedAt,
	)
	return file, err
}
