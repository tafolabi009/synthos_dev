-- Synthos Database Initialization Script
-- This script sets up the initial database schema and configurations

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS synthos;

-- Use the synthos database
\c synthos;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'user', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE subscription_status AS ENUM ('active', 'inactive', 'cancelled', 'past_due', 'trialing', 'paused');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE generation_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'partially_refunded');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role DEFAULT 'user',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create user_usage table
CREATE TABLE IF NOT EXISTS user_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    month_year VARCHAR(7) NOT NULL, -- Format: YYYY-MM
    rows_generated INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    storage_used BIGINT DEFAULT 0, -- in bytes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, month_year)
);

-- Create datasets table
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500),
    file_size BIGINT,
    row_count INTEGER,
    column_count INTEGER,
    schema_info JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create dataset_columns table
CREATE TABLE IF NOT EXISTS dataset_columns (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    nullable BOOLEAN DEFAULT true,
    unique_constraint BOOLEAN DEFAULT false,
    min_value NUMERIC,
    max_value NUMERIC,
    sample_values JSONB DEFAULT '[]'::jsonb,
    constraints JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create generation_jobs table
CREATE TABLE IF NOT EXISTS generation_jobs (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    rows_requested INTEGER NOT NULL,
    rows_generated INTEGER DEFAULT 0,
    status generation_status DEFAULT 'pending',
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    privacy_parameters JSONB DEFAULT '{}'::jsonb,
    generation_parameters JSONB DEFAULT '{}'::jsonb,
    quality_metrics JSONB DEFAULT '{}'::jsonb,
    output_s3_key VARCHAR(500),
    output_format VARCHAR(50) DEFAULT 'csv',
    output_size BIGINT,
    similarity_score DECIMAL(5,4),
    privacy_score DECIMAL(5,4),
    processing_time DECIMAL(10,3), -- in seconds
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tier_name VARCHAR(50) NOT NULL,
    status subscription_status DEFAULT 'active',
    provider VARCHAR(50) NOT NULL, -- 'paddle' or 'stripe'
    provider_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create payments table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status payment_status DEFAULT 'pending',
    provider VARCHAR(50) NOT NULL,
    provider_payment_id VARCHAR(255),
    provider_transaction_id VARCHAR(255),
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create custom_models table
CREATE TABLE IF NOT EXISTS custom_models (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    framework VARCHAR(50) NOT NULL, -- 'pytorch', 'tensorflow', 'sklearn', etc.
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0.0',
    file_path VARCHAR(500),
    file_size BIGINT,
    validation_score DECIMAL(5,4),
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    resource_id VARCHAR(255),
    resource_type VARCHAR(50),
    correlation_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create security_events table
CREATE TABLE IF NOT EXISTS security_events (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    threat_level VARCHAR(20) NOT NULL,
    source_ip INET NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    actions_taken JSONB DEFAULT '[]'::jsonb,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create webhooks table
CREATE TABLE IF NOT EXISTS webhooks (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(255) NOT NULL,
    events JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT true,
    retry_strategy VARCHAR(50) DEFAULT 'exponential',
    max_retries INTEGER DEFAULT 5,
    timeout INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create webhook_deliveries table
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    webhook_id INTEGER REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    last_response_code INTEGER,
    last_response_body TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_uuid ON users(uuid);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_datasets_owner ON datasets(owner_id);
CREATE INDEX IF NOT EXISTS idx_datasets_uuid ON datasets(uuid);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_dataset ON generation_jobs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_user ON generation_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_status ON generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_created ON generation_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_user_usage_user_month ON user_usage(user_id, month_year);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_provider ON subscriptions(provider);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_subscription ON payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider);

CREATE INDEX IF NOT EXISTS idx_custom_models_user ON custom_models(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_models_active ON custom_models(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_correlation ON audit_logs(correlation_id);

CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(source_ip);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at);
CREATE INDEX IF NOT EXISTS idx_security_events_resolved ON security_events(resolved) WHERE resolved = false;

CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhooks(user_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_created ON webhook_deliveries(created_at);

-- Create full-text search indexes
CREATE INDEX IF NOT EXISTS idx_datasets_name_gin ON datasets USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_datasets_description_gin ON datasets USING gin(to_tsvector('english', description));

-- Create composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_generation_jobs_user_status ON generation_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_dataset_status ON generation_jobs(dataset_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created ON audit_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_security_events_ip_created ON security_events(source_ip, created_at);

-- Create partial indexes for active records
CREATE INDEX IF NOT EXISTS idx_users_active_verified ON users(id) WHERE is_active = true AND is_verified = true;
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_webhooks_active_events ON webhooks(id) WHERE is_active = true;

-- Insert default admin user (password: admin123)
INSERT INTO users (email, password_hash, full_name, role, is_active, is_verified) 
VALUES (
    'admin@synthos.ai', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KzKz2K', -- admin123
    'System Administrator', 
    'admin', 
    true, 
    true
) ON CONFLICT (email) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_datasets_updated_at BEFORE UPDATE ON datasets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_custom_models_updated_at BEFORE UPDATE ON custom_models FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_webhooks_updated_at BEFORE UPDATE ON webhooks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to generate UUID v4
CREATE OR REPLACE FUNCTION generate_uuid_v4()
RETURNS UUID AS $$
BEGIN
    RETURN uuid_generate_v4();
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE synthos TO synthos;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO synthos;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO synthos;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO synthos;

-- Create views for common queries
CREATE OR REPLACE VIEW active_users AS
SELECT u.*, s.tier_name as subscription_tier, s.status as subscription_status
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
WHERE u.is_active = true;

CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.id,
    u.email,
    u.full_name,
    COUNT(DISTINCT d.id) as dataset_count,
    COUNT(DISTINCT gj.id) as generation_count,
    COALESCE(SUM(gj.rows_generated), 0) as total_rows_generated,
    COALESCE(SUM(uu.rows_generated), 0) as monthly_usage
FROM users u
LEFT JOIN datasets d ON u.id = d.owner_id
LEFT JOIN generation_jobs gj ON u.id = gj.user_id
LEFT JOIN user_usage uu ON u.id = uu.user_id
GROUP BY u.id, u.email, u.full_name;

-- Create materialized view for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS generation_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_generations,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_generations,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_generations,
    AVG(processing_time) as avg_processing_time,
    SUM(rows_generated) as total_rows_generated,
    AVG(similarity_score) as avg_similarity_score,
    AVG(privacy_score) as avg_privacy_score
FROM generation_jobs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_generation_analytics_date ON generation_analytics(date);

-- Refresh materialized view function
CREATE OR REPLACE FUNCTION refresh_generation_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW generation_analytics;
END;
$$ LANGUAGE plpgsql;

-- Set up automatic refresh (requires pg_cron extension)
-- SELECT cron.schedule('refresh-analytics', '0 0 * * *', 'SELECT refresh_generation_analytics();');

COMMIT;