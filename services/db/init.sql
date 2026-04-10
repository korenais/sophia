create table if not exists bot_messages (
  id bigserial primary key,
  user_id bigint,
  chat_id bigint not null,
  text text,
  created_at timestamp with time zone default now()
);

create index if not exists idx_bot_messages_chat_created on bot_messages(chat_id, created_at desc);

create table if not exists users (
  user_id bigint primary key,
  state text default 'ACTIVE',
  chat_id bigint,
  language text default 'en',
  username text,
  username_updated_at timestamptz,
  intro_name text,
  intro_location text,
  intro_description text,
  intro_image text,
  intro_linkedin text,
  intro_hobbies_drivers text,
  intro_skills text,
  intro_birthday date,
  field_of_activity text,
  vector_description double precision[],
  vector_location text,
  finishedonboarding boolean default false,
  user_telegram_link varchar(255),
  notifications_enabled boolean default true,
  matches_disabled boolean default false,
  last_birthday_greeting_sent date,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_users_finished_active on users(finishedonboarding, state);
create index if not exists idx_users_telegram_link on users(user_telegram_link);
create index if not exists idx_users_notifications_enabled on users(notifications_enabled);
create index if not exists idx_users_last_birthday_greeting on users(last_birthday_greeting_sent);

create table if not exists meetings (
  id bigserial primary key,
  user_1_id bigint not null references users(user_id) on delete cascade,
  user_2_id bigint not null references users(user_id) on delete cascade,
  status text not null default 'new',
  call_successful boolean,
  sent_followup_message boolean default false,
  created_at timestamptz default now(),
  last_updated timestamptz default now()
);

create index if not exists idx_meetings_users on meetings(user_1_id, user_2_id);
create index if not exists idx_meetings_status on meetings(status);

create table if not exists feedbacks (
  id bigserial primary key,
  user_id bigint not null,
  type text not null, -- 'issue' | 'feature'
  text text not null,
  created_at timestamptz default now()
);

create index if not exists idx_feedbacks_user on feedbacks(user_id, created_at desc);

create table if not exists thanks (
  id bigserial primary key,
  sender_user_id bigint not null,
  receiver_username text not null,
  sender_username text not null,
  created_at timestamptz default now()
);

create index if not exists idx_thanks_receiver on thanks(receiver_username, created_at desc);
create index if not exists idx_thanks_sender on thanks(sender_user_id, created_at desc);

-- User groups tables
create table if not exists user_groups (
  id bigserial primary key,
  name text not null unique,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists user_group_memberships (
  user_id bigint not null references users(user_id) on delete cascade,
  group_id bigint not null references user_groups(id) on delete cascade,
  created_at timestamptz default now(),
  primary key (user_id, group_id)
);

create index if not exists idx_user_group_memberships_user_id on user_group_memberships(user_id);
create index if not exists idx_user_group_memberships_group_id on user_group_memberships(group_id);
create index if not exists idx_user_groups_name on user_groups(name);

-- Notifications table
create table if not exists notifications (
  id bigserial primary key,
  message_text text not null,
  scheduled_at timestamptz,
  sent_at timestamptz,
  status text not null default 'scheduled', -- 'scheduled', 'sent', 'cancelled'
  recipient_type text not null default 'all', -- 'all', 'user', 'group', 'user_group'
  recipient_ids bigint[], -- array of user_ids for 'user' or 'group' types
  image_url text,
  sent_count integer default 0,
  failed_count integer default 0,
  error_message text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_notifications_status on notifications(status);
create index if not exists idx_notifications_scheduled_at on notifications(scheduled_at) where status = 'scheduled';
create index if not exists idx_notifications_created_at on notifications(created_at desc);

-- Match blocks table
create table if not exists match_blocks (
    id bigserial primary key,
    user_id bigint not null references users(user_id) on delete cascade,
    blocked_user_id bigint not null references users(user_id) on delete cascade,
    created_at timestamptz default now(),
    unique(user_id, blocked_user_id)
);

create index if not exists idx_match_blocks_user on match_blocks(user_id);
create index if not exists idx_match_blocks_blocked on match_blocks(blocked_user_id);
create index if not exists idx_match_blocks_pair on match_blocks(user_id, blocked_user_id);

