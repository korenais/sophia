-- Add notifications_enabled column to users table
alter table if exists users 
add column if not exists notifications_enabled boolean default true;

create index if not exists idx_users_notifications_enabled on users(notifications_enabled);

-- Create notifications table
create table if not exists notifications (
  id bigserial primary key,
  message_text text not null,
  scheduled_at timestamptz,
  sent_at timestamptz,
  status text not null default 'scheduled', -- 'scheduled', 'sent', 'cancelled'
  recipient_type text not null default 'all', -- 'all', 'user', 'group'
  recipient_ids bigint[], -- array of user_ids for 'user' or 'group' types
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_notifications_status on notifications(status);
create index if not exists idx_notifications_scheduled_at on notifications(scheduled_at) where status = 'scheduled';
create index if not exists idx_notifications_created_at on notifications(created_at desc);
