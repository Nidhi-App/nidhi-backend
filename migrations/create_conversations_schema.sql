-- Migration: Create Conversations and Messages Schema
-- Purpose: Store chat conversations and messages for text2sql chatbot
-- Created: 2025-10-23

-- ============================================================================
-- 1. CREATE ENUM TYPES
-- ============================================================================

-- Message role enum
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

-- ============================================================================
-- 2. CREATE CONVERSATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_message_at TIMESTAMP WITH TIME ZONE,
    is_archived BOOLEAN DEFAULT FALSE NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL, -- Soft delete for audit trail
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT conversations_title_length CHECK (char_length(title) <= 255),
    CONSTRAINT conversations_valid_dates CHECK (created_at <= updated_at)
);

-- ============================================================================
-- 3. CREATE MESSAGES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,

    -- SQL and execution details (for assistant messages)
    sql_query TEXT,
    sql_params JSONB,
    query_results_summary JSONB, -- Store {row_count, sample_rows: first 5}
    execution_time NUMERIC(10, 3), -- Seconds with millisecond precision
    error TEXT,

    -- Model and tracking info
    model_version VARCHAR(100), -- e.g., 'gpt-4', 'gpt-5'
    token_count INTEGER, -- For cost tracking

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb, -- Store cache_hit, cache_miss, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT messages_content_length CHECK (char_length(content) <= 10000),
    CONSTRAINT messages_execution_time_positive CHECK (execution_time IS NULL OR execution_time >= 0),
    CONSTRAINT messages_token_count_positive CHECK (token_count IS NULL OR token_count >= 0)
);

-- ============================================================================
-- 4. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Conversation indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id
    ON conversations(user_id, last_message_at DESC NULLS LAST)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_conversations_archived
    ON conversations(user_id, is_archived)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_conversations_created_at
    ON conversations(user_id, created_at DESC)
    WHERE is_deleted = FALSE;

-- Message indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_messages_role
    ON messages(conversation_id, role);

-- Full-text search on messages (future enhancement)
CREATE INDEX IF NOT EXISTS idx_messages_content_search
    ON messages USING gin(to_tsvector('english', content));

-- ============================================================================
-- 5. CREATE TRIGGER TO UPDATE updated_at
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on conversations table
DROP TRIGGER IF EXISTS trigger_update_conversations_updated_at ON conversations;
CREATE TRIGGER trigger_update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversations_updated_at();

-- ============================================================================
-- 6. CREATE TRIGGER TO UPDATE last_message_at
-- ============================================================================

-- Function to update last_message_at when message is added
CREATE OR REPLACE FUNCTION update_conversation_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on messages table
DROP TRIGGER IF EXISTS trigger_update_conversation_last_message ON messages;
CREATE TRIGGER trigger_update_conversation_last_message
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();

-- ============================================================================
-- 7. ROW-LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on both tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Conversations RLS Policies
-- ============================================================================

-- Policy: Users can SELECT their own conversations
DROP POLICY IF EXISTS conversations_select_own ON conversations;
CREATE POLICY conversations_select_own
    ON conversations
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can INSERT their own conversations
DROP POLICY IF EXISTS conversations_insert_own ON conversations;
CREATE POLICY conversations_insert_own
    ON conversations
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can UPDATE their own conversations
DROP POLICY IF EXISTS conversations_update_own ON conversations;
CREATE POLICY conversations_update_own
    ON conversations
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can DELETE their own conversations (soft delete via UPDATE)
DROP POLICY IF EXISTS conversations_delete_own ON conversations;
CREATE POLICY conversations_delete_own
    ON conversations
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- Messages RLS Policies
-- ============================================================================

-- Policy: Users can SELECT messages from their conversations
DROP POLICY IF EXISTS messages_select_own ON messages;
CREATE POLICY messages_select_own
    ON messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.conversation_id = messages.conversation_id
            AND conversations.user_id = auth.uid()
        )
    );

-- Policy: Users can INSERT messages to their conversations
DROP POLICY IF EXISTS messages_insert_own ON messages;
CREATE POLICY messages_insert_own
    ON messages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.conversation_id = messages.conversation_id
            AND conversations.user_id = auth.uid()
        )
    );

-- Note: No UPDATE or DELETE policies for messages to preserve history

-- ============================================================================
-- 8. HELPER FUNCTIONS
-- ============================================================================

-- Function to get conversation message count
CREATE OR REPLACE FUNCTION get_conversation_message_count(conv_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER
        FROM messages
        WHERE conversation_id = conv_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get last N messages for context
CREATE OR REPLACE FUNCTION get_last_n_messages(conv_id UUID, n INTEGER DEFAULT 10)
RETURNS TABLE (
    message_id UUID,
    role message_role,
    content TEXT,
    sql_query TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.message_id,
        m.role,
        m.content,
        m.sql_query,
        m.created_at
    FROM messages m
    WHERE m.conversation_id = conv_id
    ORDER BY m.created_at DESC
    LIMIT n;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 9. GRANT PERMISSIONS
-- ============================================================================

-- Grant access to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON conversations TO authenticated;
GRANT SELECT, INSERT ON messages TO authenticated;
GRANT USAGE ON TYPE message_role TO authenticated;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION get_conversation_message_count TO authenticated;
GRANT EXECUTE ON FUNCTION get_last_n_messages TO authenticated;

-- ============================================================================
-- 10. COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE conversations IS 'Stores user chat conversations for the text2sql chatbot';
COMMENT ON TABLE messages IS 'Stores individual messages within conversations, preserving full history';

COMMENT ON COLUMN conversations.is_archived IS 'Soft archive flag - archived conversations hidden from default view';
COMMENT ON COLUMN conversations.is_deleted IS 'Soft delete flag for audit trail - deleted conversations can be recovered';
COMMENT ON COLUMN conversations.metadata IS 'Extensible metadata field for tags, settings, etc.';

COMMENT ON COLUMN messages.query_results_summary IS 'Summary of query results: {row_count: N, sample_rows: [...first 5 rows]}';
COMMENT ON COLUMN messages.metadata IS 'Stores cache_hit, cache_miss, model_temperature, etc.';
COMMENT ON COLUMN messages.token_count IS 'Token count for cost tracking and analytics';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
