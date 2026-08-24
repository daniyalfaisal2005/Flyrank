CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE
);

-- Optional starter rows (inserted only once)
INSERT INTO tasks (title, done)
SELECT seed.title, seed.done
FROM (VALUES
    ('Write project proposal', FALSE),
    ('Review sprint notes', TRUE),
    ('Plan next task', FALSE)
) AS seed(title, done)
WHERE NOT EXISTS (SELECT 1 FROM tasks);
