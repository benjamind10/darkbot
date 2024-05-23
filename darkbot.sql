create table users
(
    id           serial
        primary key,
    name         varchar,
    discorduser  bigint
        constraint unique_discorduser
            unique,
    bgguser      varchar,
    isenabled    boolean   default true,
    datemodified timestamp default CURRENT_TIMESTAMP
);

alter table users
    owner to postgres;

create table boardgames
(
    id           serial
        primary key,
    userid       integer       not null
        references users,
    name         varchar(1000) not null,
    bggid        integer       not null,
    avgrating    double precision,
    own          boolean   default false,
    prevowned    boolean   default false,
    fortrade     boolean   default false,
    want         boolean   default false,
    wanttoplay   boolean   default false,
    wanttobuy    boolean   default false,
    wishlist     boolean   default false,
    preordered   boolean   default false,
    datemodified timestamp default CURRENT_TIMESTAMP,
    minplayers   integer,
    maxplayers   integer,
    minplaytime  integer,
    numplays     integer,
    constraint unique_userid_bggid
        unique (userid, bggid)
);

alter table boardgames
    owner to postgres;

create view boardgames_stats (boardgamename, username, avgrating, minplayers, maxplayers, minplaytime, numplays) as
SELECT DISTINCT ON (bg.name) bg.name AS boardgamename,
                             u.name  AS username,
                             bg.avgrating,
                             bg.minplayers,
                             bg.maxplayers,
                             bg.minplaytime,
                             bg.numplays
FROM boardgames bg
         JOIN users u ON bg.userid = u.id
ORDER BY bg.name, bg.avgrating DESC;

alter table boardgames_stats
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

create trigger trigger_update_modified
    before update
    on boardgames
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

create function get_all_bggusers()
    returns TABLE(id integer, bgguser character varying)
    language plpgsql
as
$$
BEGIN
    RETURN QUERY
    SELECT users.id, users.bgguser FROM users WHERE users.bgguser IS NOT NULL;
END;
$$;

alter function get_all_bggusers() owner to postgres;

create function upsert_boardgame(p_userid integer, p_name character varying, p_bggid integer, p_avgrating double precision, p_own boolean, p_prevowned boolean, p_fortrade boolean, p_want boolean, p_wanttoplay boolean, p_wanttobuy boolean, p_wishlist boolean, p_preordered boolean, p_minplayers integer, p_maxplayers integer, p_minplaytime integer, p_numplays integer) returns text
    language plpgsql
as
$$
DECLARE
    result_id INTEGER;
BEGIN
    INSERT INTO boardgames (userid, name, bggid, avgrating, own, prevowned, fortrade, want, wanttoplay, wanttobuy,
                            wishlist, preordered, minplayers, maxplayers, minplaytime, numplays)
    VALUES (p_userid, p_name, p_bggid, p_avgrating, p_own, p_prevowned, p_fortrade, p_want, p_wanttoplay, p_wanttobuy,
            p_wishlist, p_preordered, p_minplayers, p_maxplayers, p_minplaytime, p_numplays)
    ON CONFLICT (userid, bggid) DO UPDATE SET
                                      name        = EXCLUDED.name,
                                      avgrating   = EXCLUDED.avgrating,
                                      own         = EXCLUDED.own,
                                      prevowned   = EXCLUDED.prevowned,
                                      fortrade    = EXCLUDED.fortrade,
                                      want        = EXCLUDED.want,
                                      wanttoplay  = EXCLUDED.wanttoplay,
                                      wanttobuy   = EXCLUDED.wanttobuy,
                                      wishlist    = EXCLUDED.wishlist,
                                      preordered  = EXCLUDED.preordered,
                                      minplayers  = EXCLUDED.minplayers,
                                      maxplayers  = EXCLUDED.maxplayers,
                                      minplaytime = EXCLUDED.minplaytime,
                                      numplays    = EXCLUDED.numplays
    RETURNING id INTO result_id;

    RETURN 'Boardgame ID: ' || result_id::TEXT;
EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$;

alter function upsert_boardgame(integer, varchar, integer, double precision, boolean, boolean, boolean, boolean, boolean, boolean, boolean, boolean, integer, integer, integer, integer) owner to postgres;

create function upsert_user(_name text, _discorduser bigint, _bgguser text, _isenabled boolean) returns text
    language plpgsql
as
$$
DECLARE
    result_id INT;
BEGIN
    INSERT INTO Users (Name, DiscordUser, BGGUser, IsEnabled)
    VALUES (_name, _discorduser, _bgguser, _isenabled)
    ON CONFLICT (DiscordUser) DO UPDATE SET Name        = EXCLUDED.Name,
                                      BGGUser     = EXCLUDED.BGGUser,
                                      IsEnabled   = EXCLUDED.IsEnabled
    RETURNING ID INTO result_id;

    RETURN 'User ID: ' || result_id::TEXT;
EXCEPTION
    WHEN OTHERS THEN
        RETURN 'Error: ' || SQLERRM;
END;
$$;

alter function upsert_user(text, bigint, text, boolean) owner to postgres;

create function get_enabled_users()
    returns TABLE(id integer, name text, discorduser bigint, bgguser text, isenabled boolean)
    language sql
as
$$
    SELECT id, name, discorduser, bgguser, isenabled
    FROM Users
    WHERE isenabled = TRUE;
$$;

alter function get_enabled_users() owner to postgres;

create function get_boardgames_starting_with(letter character)
    returns TABLE(id integer, userid integer, username text, name text, bggid integer, avgrating double precision, own boolean, prevowned boolean, fortrade boolean, want boolean, wanttoplay boolean, wanttobuy boolean, wishlist boolean, preordered boolean, datemodified timestamp without time zone, minplayers integer, maxplayers integer, minplaytime integer, numplays integer)
    language sql
as
$$
WITH DistinctGames AS (
    SELECT DISTINCT ON (bg.name)
        bg.id,
        bg.userid,
        u.name AS username,
        bg.name,
        bg.bggid,
        bg.avgrating,
        bg.own,
        bg.prevowned,
        bg.fortrade,
        bg.want,
        bg.wanttoplay,
        bg.wanttobuy,
        bg.wishlist,
        bg.preordered,
        bg.datemodified,
        bg.minplayers,
        bg.maxplayers,
        bg.minplaytime,
        bg.numplays
    FROM BoardGames bg
    JOIN Users u ON bg.userid = u.id
    WHERE bg.Name ILIKE letter || '%' AND bg.own = TRUE
    ORDER BY bg.name
)
SELECT *
FROM DistinctGames
WHERE avgrating > 7.5
ORDER BY avgrating DESC;
$$;

alter function get_boardgames_starting_with(char) owner to postgres;

