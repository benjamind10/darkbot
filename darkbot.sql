create table users
(
    id           serial
        primary key,
    name         varchar,
    email        varchar
        constraint email_unique
            unique,
    discorduser  bigint,
    bgguser      varchar,
    isenabled    boolean   default true,
    datemodified timestamp default CURRENT_TIMESTAMP
);

alter table users
    owner to postgres;

create function update_modified_column() returns trigger
    language plpgsql
as
$$
BEGIN
    NEW.DateModified = now();
    RETURN NEW;
END;
$$;

alter function update_modified_column() owner to postgres;

create trigger trigger_update_user_modtime
    before update
    on users
    for each row
execute procedure update_modified_column();

create function disable_user(user_id integer) returns void
    language plpgsql
as
$$
BEGIN
    UPDATE Users
    SET IsEnabled = false
    WHERE ID = user_id;
END;
$$;

alter function disable_user(integer) owner to postgres;

create function upsert_user(_name text, _email text, _discorduser bigint, _bgguser text, _isenabled boolean) returns text
    language plpgsql
as
$$
DECLARE
    result_id INT;
BEGIN
    INSERT INTO Users (Name, email, DiscordUser, BGGUser, IsEnabled)
    VALUES (_name, _email, _discorduser, _bgguser, _isenabled)
    ON CONFLICT (email) DO UPDATE SET
        Name = EXCLUDED.Name,
        DiscordUser = EXCLUDED.DiscordUser,
        BGGUser = EXCLUDED.BGGUser,
        IsEnabled = EXCLUDED.IsEnabled
    RETURNING ID INTO result_id;

    RETURN 'User ID: ' || result_id::TEXT; -- Convert result_id to text and return it
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error: ' || SQLERRM;
END;
$$;

alter function upsert_user(text, text, bigint, text, boolean) owner to postgres;

create function enable_user(user_id integer) returns text
    language plpgsql
as
$$
BEGIN
    UPDATE Users
    SET IsEnabled = true, DateModified = CURRENT_TIMESTAMP
    WHERE ID = user_id;

    IF FOUND THEN
        RETURN 'User successfully enabled.';
    ELSE
        RETURN 'No user found with the given ID.';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error enabling user: ' || SQLERRM;
END;
$$;

alter function enable_user(integer) owner to postgres;


