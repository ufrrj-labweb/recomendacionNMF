CREATE TABLE IF NOT EXISTS notifications_sent (
  id SERIAL PRIMARY KEY,
  class_id INT NOT NULL,
  user_id INT NOT NULL,
  sent_at TIMESTAMP NOT NULL DEFAULT now(),
  UNIQUE (class_id, user_id)
);
