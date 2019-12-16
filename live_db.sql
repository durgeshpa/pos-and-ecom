--
-- PostgreSQL database dump
--

-- Dumped from database version 10.4
-- Dumped by pg_dump version 10.6 (Ubuntu 10.6-0ubuntu0.18.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: account_emailaddress; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.account_emailaddress (
    id integer NOT NULL,
    email character varying(254) NOT NULL,
    verified boolean NOT NULL,
    "primary" boolean NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.account_emailaddress OWNER TO gramfac18;

--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.account_emailaddress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.account_emailaddress_id_seq OWNER TO gramfac18;

--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.account_emailaddress_id_seq OWNED BY public.account_emailaddress.id;


--
-- Name: account_emailconfirmation; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.account_emailconfirmation (
    id integer NOT NULL,
    created timestamp with time zone NOT NULL,
    sent timestamp with time zone,
    key character varying(64) NOT NULL,
    email_address_id integer NOT NULL
);


ALTER TABLE public.account_emailconfirmation OWNER TO gramfac18;

--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.account_emailconfirmation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.account_emailconfirmation_id_seq OWNER TO gramfac18;

--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.account_emailconfirmation_id_seq OWNED BY public.account_emailconfirmation.id;


--
-- Name: accounts_user; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.accounts_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    first_name character varying(30) NOT NULL,
    last_name character varying(150) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    phone_number character varying(10) NOT NULL,
    email character varying(254) NOT NULL,
    user_photo character varying(100),
    user_type smallint,
    CONSTRAINT accounts_user_user_type_check CHECK ((user_type >= 0))
);


ALTER TABLE public.accounts_user OWNER TO gramfac18;

--
-- Name: accounts_user_groups; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.accounts_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.accounts_user_groups OWNER TO gramfac18;

--
-- Name: accounts_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.accounts_user_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.accounts_user_groups_id_seq OWNER TO gramfac18;

--
-- Name: accounts_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.accounts_user_groups_id_seq OWNED BY public.accounts_user_groups.id;


--
-- Name: accounts_user_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.accounts_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.accounts_user_id_seq OWNER TO gramfac18;

--
-- Name: accounts_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.accounts_user_id_seq OWNED BY public.accounts_user.id;


--
-- Name: accounts_user_user_permissions; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.accounts_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.accounts_user_user_permissions OWNER TO gramfac18;

--
-- Name: accounts_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.accounts_user_user_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.accounts_user_user_permissions_id_seq OWNER TO gramfac18;

--
-- Name: accounts_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.accounts_user_user_permissions_id_seq OWNED BY public.accounts_user_user_permissions.id;


--
-- Name: accounts_userdocument; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.accounts_userdocument (
    id integer NOT NULL,
    user_document_type character varying(100) NOT NULL,
    user_document_number character varying(100) NOT NULL,
    user_document_photo character varying(100) NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.accounts_userdocument OWNER TO gramfac18;

--
-- Name: accounts_userdocument_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.accounts_userdocument_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.accounts_userdocument_id_seq OWNER TO gramfac18;

--
-- Name: accounts_userdocument_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.accounts_userdocument_id_seq OWNED BY public.accounts_userdocument.id;


--
-- Name: addresses_address; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.addresses_address (
    id integer NOT NULL,
    nick_name character varying(255),
    address_line1 character varying(255) NOT NULL,
    address_contact_name character varying(255),
    address_contact_number character varying(10) NOT NULL,
    pincode character varying(6) NOT NULL,
    address_type character varying(255) NOT NULL,
    latitude double precision,
    longitude double precision,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    city_id integer NOT NULL,
    shop_name_id integer,
    state_id integer
);


ALTER TABLE public.addresses_address OWNER TO gramfac18;

--
-- Name: addresses_address_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.addresses_address_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_address_id_seq OWNER TO gramfac18;

--
-- Name: addresses_address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.addresses_address_id_seq OWNED BY public.addresses_address.id;


--
-- Name: addresses_area; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.addresses_area (
    id integer NOT NULL,
    area_name character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    city_id integer
);


ALTER TABLE public.addresses_area OWNER TO gramfac18;

--
-- Name: addresses_area_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.addresses_area_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_area_id_seq OWNER TO gramfac18;

--
-- Name: addresses_area_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.addresses_area_id_seq OWNED BY public.addresses_area.id;


--
-- Name: addresses_city; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.addresses_city (
    id integer NOT NULL,
    city_name character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    country_id integer,
    state_id integer
);


ALTER TABLE public.addresses_city OWNER TO gramfac18;

--
-- Name: addresses_city_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.addresses_city_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_city_id_seq OWNER TO gramfac18;

--
-- Name: addresses_city_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.addresses_city_id_seq OWNED BY public.addresses_city.id;


--
-- Name: addresses_country; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.addresses_country (
    id integer NOT NULL,
    country_name character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.addresses_country OWNER TO gramfac18;

--
-- Name: addresses_country_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.addresses_country_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_country_id_seq OWNER TO gramfac18;

--
-- Name: addresses_country_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.addresses_country_id_seq OWNED BY public.addresses_country.id;


--
-- Name: addresses_invoicecitymapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.addresses_invoicecitymapping (
    id integer NOT NULL,
    city_code character varying(255) NOT NULL,
    city_id integer NOT NULL
);


ALTER TABLE public.addresses_invoicecitymapping OWNER TO gramfac18;

--
-- Name: addresses_invoicecitymapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.addresses_invoicecitymapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_invoicecitymapping_id_seq OWNER TO gramfac18;

--
-- Name: addresses_invoicecitymapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.addresses_invoicecitymapping_id_seq OWNED BY public.addresses_invoicecitymapping.id;


--
-- Name: addresses_state; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.addresses_state (
    id integer NOT NULL,
    state_name character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    country_id integer
);


ALTER TABLE public.addresses_state OWNER TO gramfac18;

--
-- Name: addresses_state_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.addresses_state_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_state_id_seq OWNER TO gramfac18;

--
-- Name: addresses_state_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.addresses_state_id_seq OWNED BY public.addresses_state.id;


--
-- Name: allauth_socialaccount; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.allauth_socialaccount (
    id integer NOT NULL,
    provider character varying(30) NOT NULL,
    uid character varying(191) NOT NULL,
    last_login timestamp with time zone NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    extra_data text NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.allauth_socialaccount OWNER TO gramfac18;

--
-- Name: allauth_socialaccount_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.allauth_socialaccount_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.allauth_socialaccount_id_seq OWNER TO gramfac18;

--
-- Name: allauth_socialaccount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.allauth_socialaccount_id_seq OWNED BY public.allauth_socialaccount.id;


--
-- Name: allauth_socialapp; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.allauth_socialapp (
    id integer NOT NULL,
    provider character varying(30) NOT NULL,
    name character varying(40) NOT NULL,
    client_id character varying(191) NOT NULL,
    secret character varying(191) NOT NULL,
    key character varying(191) NOT NULL
);


ALTER TABLE public.allauth_socialapp OWNER TO gramfac18;

--
-- Name: allauth_socialapp_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.allauth_socialapp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.allauth_socialapp_id_seq OWNER TO gramfac18;

--
-- Name: allauth_socialapp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.allauth_socialapp_id_seq OWNED BY public.allauth_socialapp.id;


--
-- Name: allauth_socialapp_sites; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.allauth_socialapp_sites (
    id integer NOT NULL,
    socialapp_id integer NOT NULL,
    site_id integer NOT NULL
);


ALTER TABLE public.allauth_socialapp_sites OWNER TO gramfac18;

--
-- Name: allauth_socialapp_sites_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.allauth_socialapp_sites_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.allauth_socialapp_sites_id_seq OWNER TO gramfac18;

--
-- Name: allauth_socialapp_sites_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.allauth_socialapp_sites_id_seq OWNED BY public.allauth_socialapp_sites.id;


--
-- Name: allauth_socialtoken; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.allauth_socialtoken (
    id integer NOT NULL,
    token text NOT NULL,
    token_secret text NOT NULL,
    expires_at timestamp with time zone,
    account_id integer NOT NULL,
    app_id integer NOT NULL
);


ALTER TABLE public.allauth_socialtoken OWNER TO gramfac18;

--
-- Name: allauth_socialtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.allauth_socialtoken_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.allauth_socialtoken_id_seq OWNER TO gramfac18;

--
-- Name: allauth_socialtoken_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.allauth_socialtoken_id_seq OWNED BY public.allauth_socialtoken.id;


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(80) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO gramfac18;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.auth_group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO gramfac18;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO gramfac18;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.auth_group_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_permissions_id_seq OWNER TO gramfac18;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO gramfac18;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.auth_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO gramfac18;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- Name: authtoken_token; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.authtoken_token (
    key character varying(40) NOT NULL,
    created timestamp with time zone NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.authtoken_token OWNER TO gramfac18;

--
-- Name: banner_banner; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.banner_banner (
    id integer NOT NULL,
    name character varying(20),
    image character varying(100),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    banner_start_date timestamp with time zone,
    banner_end_date timestamp with time zone,
    status boolean NOT NULL,
    alt_text character varying(20),
    text_below_image character varying(20)
);


ALTER TABLE public.banner_banner OWNER TO gramfac18;

--
-- Name: banner_banner_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.banner_banner_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.banner_banner_id_seq OWNER TO gramfac18;

--
-- Name: banner_banner_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.banner_banner_id_seq OWNED BY public.banner_banner.id;


--
-- Name: banner_bannerdata; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.banner_bannerdata (
    id integer NOT NULL,
    banner_data_order integer NOT NULL,
    banner_data_id integer,
    slot_id integer NOT NULL,
    CONSTRAINT banner_bannerdata_banner_data_order_check CHECK ((banner_data_order >= 0))
);


ALTER TABLE public.banner_bannerdata OWNER TO gramfac18;

--
-- Name: banner_bannerdata_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.banner_bannerdata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.banner_bannerdata_id_seq OWNER TO gramfac18;

--
-- Name: banner_bannerdata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.banner_bannerdata_id_seq OWNED BY public.banner_bannerdata.id;


--
-- Name: banner_bannerposition; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.banner_bannerposition (
    id integer NOT NULL,
    banner_position_order integer NOT NULL,
    bannerslot_id integer,
    page_id integer,
    CONSTRAINT banner_bannerposition_banner_position_order_check CHECK ((banner_position_order >= 0))
);


ALTER TABLE public.banner_bannerposition OWNER TO gramfac18;

--
-- Name: banner_bannerposition_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.banner_bannerposition_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.banner_bannerposition_id_seq OWNER TO gramfac18;

--
-- Name: banner_bannerposition_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.banner_bannerposition_id_seq OWNED BY public.banner_bannerposition.id;


--
-- Name: banner_bannerslot; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.banner_bannerslot (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    page_id integer
);


ALTER TABLE public.banner_bannerslot OWNER TO gramfac18;

--
-- Name: banner_bannerslot_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.banner_bannerslot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.banner_bannerslot_id_seq OWNER TO gramfac18;

--
-- Name: banner_bannerslot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.banner_bannerslot_id_seq OWNED BY public.banner_bannerslot.id;


--
-- Name: banner_page; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.banner_page (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);


ALTER TABLE public.banner_page OWNER TO gramfac18;

--
-- Name: banner_page_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.banner_page_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.banner_page_id_seq OWNER TO gramfac18;

--
-- Name: banner_page_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.banner_page_id_seq OWNED BY public.banner_page.id;


--
-- Name: brand_brand; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.brand_brand (
    id integer NOT NULL,
    brand_name character varying(20) NOT NULL,
    brand_slug character varying(50),
    brand_logo character varying(100),
    brand_description text,
    brand_code character varying(3) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    active_status smallint NOT NULL,
    brand_parent_id integer,
    CONSTRAINT brand_brand_active_status_check CHECK ((active_status >= 0))
);


ALTER TABLE public.brand_brand OWNER TO gramfac18;

--
-- Name: brand_brand_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.brand_brand_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.brand_brand_id_seq OWNER TO gramfac18;

--
-- Name: brand_brand_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.brand_brand_id_seq OWNED BY public.brand_brand.id;


--
-- Name: brand_branddata; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.brand_branddata (
    id integer NOT NULL,
    brand_data_order integer NOT NULL,
    brand_data_id integer,
    slot_id integer,
    CONSTRAINT brand_branddata_brand_data_order_check CHECK ((brand_data_order >= 0))
);


ALTER TABLE public.brand_branddata OWNER TO gramfac18;

--
-- Name: brand_branddata_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.brand_branddata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.brand_branddata_id_seq OWNER TO gramfac18;

--
-- Name: brand_branddata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.brand_branddata_id_seq OWNED BY public.brand_branddata.id;


--
-- Name: brand_brandposition; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.brand_brandposition (
    id integer NOT NULL,
    position_name character varying(255) NOT NULL,
    brand_position_order integer NOT NULL,
    CONSTRAINT brand_brandposition_brand_position_order_check CHECK ((brand_position_order >= 0))
);


ALTER TABLE public.brand_brandposition OWNER TO gramfac18;

--
-- Name: brand_brandposition_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.brand_brandposition_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.brand_brandposition_id_seq OWNER TO gramfac18;

--
-- Name: brand_brandposition_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.brand_brandposition_id_seq OWNED BY public.brand_brandposition.id;


--
-- Name: brand_vendor; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.brand_vendor (
    id integer NOT NULL,
    company_name character varying(255),
    vendor_name character varying(255),
    contact_person_name character varying(255),
    telephone_no character varying(15),
    mobile character varying(10),
    designation character varying(255),
    address_line1 character varying(255),
    pincode character varying(6),
    payment_terms text,
    vendor_registion_free character varying(50),
    sku_listing_free character varying(50),
    return_policy text,
    "GST_number" character varying(100),
    "MSMED_reg_no" character varying(100),
    "MSMED_reg_document" character varying(100),
    fssai_licence character varying(100),
    "GST_document" character varying(100),
    pan_card character varying(100),
    cancelled_cheque character varying(100),
    "list_of_sku_in_NPI_formate" character varying(100),
    vendor_form character varying(100),
    vendor_products_csv character varying(100),
    city_id integer,
    state_id integer
);


ALTER TABLE public.brand_vendor OWNER TO gramfac18;

--
-- Name: brand_vendor_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.brand_vendor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.brand_vendor_id_seq OWNER TO gramfac18;

--
-- Name: brand_vendor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.brand_vendor_id_seq OWNED BY public.brand_vendor.id;


--
-- Name: categories_category; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.categories_category (
    id integer NOT NULL,
    category_name character varying(255) NOT NULL,
    category_slug character varying(50) NOT NULL,
    category_desc text,
    category_sku_part character varying(3) NOT NULL,
    category_image character varying(100),
    is_created timestamp with time zone NOT NULL,
    is_modified timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    category_parent_id integer
);


ALTER TABLE public.categories_category OWNER TO gramfac18;

--
-- Name: categories_category_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.categories_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.categories_category_id_seq OWNER TO gramfac18;

--
-- Name: categories_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.categories_category_id_seq OWNED BY public.categories_category.id;


--
-- Name: categories_categorydata; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.categories_categorydata (
    id integer NOT NULL,
    category_data_order integer NOT NULL,
    category_data_id integer,
    category_pos_id integer,
    CONSTRAINT categories_categorydata_category_data_order_check CHECK ((category_data_order >= 0))
);


ALTER TABLE public.categories_categorydata OWNER TO gramfac18;

--
-- Name: categories_categorydata_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.categories_categorydata_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.categories_categorydata_id_seq OWNER TO gramfac18;

--
-- Name: categories_categorydata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.categories_categorydata_id_seq OWNED BY public.categories_categorydata.id;


--
-- Name: categories_categoryposation; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.categories_categoryposation (
    id integer NOT NULL,
    posation_name character varying(255) NOT NULL,
    category_posation_order integer NOT NULL,
    CONSTRAINT categories_categoryposation_category_posation_order_check CHECK ((category_posation_order >= 0))
);


ALTER TABLE public.categories_categoryposation OWNER TO gramfac18;

--
-- Name: categories_categoryposation_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.categories_categoryposation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.categories_categoryposation_id_seq OWNER TO gramfac18;

--
-- Name: categories_categoryposation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.categories_categoryposation_id_seq OWNED BY public.categories_categoryposation.id;


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO gramfac18;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.django_admin_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_admin_log_id_seq OWNER TO gramfac18;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.django_admin_log_id_seq OWNED BY public.django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO gramfac18;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.django_content_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_content_type_id_seq OWNER TO gramfac18;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO gramfac18;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.django_migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_migrations_id_seq OWNER TO gramfac18;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.django_migrations_id_seq OWNED BY public.django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO gramfac18;

--
-- Name: django_site; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.django_site (
    id integer NOT NULL,
    domain character varying(100) NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.django_site OWNER TO gramfac18;

--
-- Name: django_site_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.django_site_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_site_id_seq OWNER TO gramfac18;

--
-- Name: django_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.django_site_id_seq OWNED BY public.django_site.id;


--
-- Name: gram_to_brand_brandnote; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_brandnote (
    id integer NOT NULL,
    brand_note_id character varying(255),
    note_type character varying(255) NOT NULL,
    amount double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    grn_order_id integer,
    last_modified_by_id integer,
    order_id integer
);


ALTER TABLE public.gram_to_brand_brandnote OWNER TO gramfac18;

--
-- Name: gram_to_brand_brandnote_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_brandnote_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_brandnote_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_brandnote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_brandnote_id_seq OWNED BY public.gram_to_brand_brandnote.id;


--
-- Name: gram_to_brand_cart; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_cart (
    id integer NOT NULL,
    po_no character varying(255),
    po_status character varying(200),
    po_creation_date date NOT NULL,
    po_validity_date date NOT NULL,
    payment_term text,
    delivery_term text,
    po_amount double precision NOT NULL,
    cart_product_mapping_csv character varying(100),
    is_approve boolean,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    brand_id integer NOT NULL,
    gf_billing_address_id integer,
    gf_shipping_address_id integer,
    last_modified_by_id integer,
    po_message_id integer,
    po_raised_by_id integer,
    shop_id integer,
    supplier_name_id integer,
    supplier_state_id integer
);


ALTER TABLE public.gram_to_brand_cart OWNER TO gramfac18;

--
-- Name: gram_to_brand_cart_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_cart_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_cart_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_cart_id_seq OWNED BY public.gram_to_brand_cart.id;


--
-- Name: gram_to_brand_cartproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_cartproductmapping (
    id integer NOT NULL,
    inner_case_size integer NOT NULL,
    case_size integer NOT NULL,
    number_of_cases integer NOT NULL,
    qty integer NOT NULL,
    scheme double precision,
    price double precision NOT NULL,
    total_price integer NOT NULL,
    cart_id integer NOT NULL,
    cart_product_id integer NOT NULL,
    CONSTRAINT gram_to_brand_cartproductmapping_case_size_check CHECK ((case_size >= 0)),
    CONSTRAINT gram_to_brand_cartproductmapping_inner_case_size_check CHECK ((inner_case_size >= 0)),
    CONSTRAINT gram_to_brand_cartproductmapping_number_of_cases_check CHECK ((number_of_cases >= 0)),
    CONSTRAINT gram_to_brand_cartproductmapping_qty_check CHECK ((qty >= 0)),
    CONSTRAINT gram_to_brand_cartproductmapping_total_price_check CHECK ((total_price >= 0))
);


ALTER TABLE public.gram_to_brand_cartproductmapping OWNER TO gramfac18;

--
-- Name: gram_to_brand_cartproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_cartproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_cartproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_cartproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_cartproductmapping_id_seq OWNED BY public.gram_to_brand_cartproductmapping.id;


--
-- Name: gram_to_brand_grnorder; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_grnorder (
    id integer NOT NULL,
    invoice_no character varying(255) NOT NULL,
    grn_id character varying(255),
    grn_date date NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer,
    order_item_id integer
);


ALTER TABLE public.gram_to_brand_grnorder OWNER TO gramfac18;

--
-- Name: gram_to_brand_grnorder_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_grnorder_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_grnorder_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_grnorder_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_grnorder_id_seq OWNED BY public.gram_to_brand_grnorder.id;


--
-- Name: gram_to_brand_grnorderproducthistory; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_grnorderproducthistory (
    id integer NOT NULL,
    invoice_no character varying(255) NOT NULL,
    grn_id character varying(255),
    changed_price double precision NOT NULL,
    manufacture_date date,
    expiry_date date,
    available_qty integer NOT NULL,
    ordered_qty integer NOT NULL,
    delivered_qty integer NOT NULL,
    returned_qty integer NOT NULL,
    damaged_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    grn_order_id integer,
    last_modified_by_id integer,
    order_id integer,
    order_item_id integer,
    product_id integer,
    CONSTRAINT gram_to_brand_grnorderproducthistory_available_qty_check CHECK ((available_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproducthistory_damaged_qty_check CHECK ((damaged_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproducthistory_delivered_qty_check CHECK ((delivered_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproducthistory_ordered_qty_check CHECK ((ordered_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproducthistory_returned_qty_check CHECK ((returned_qty >= 0))
);


ALTER TABLE public.gram_to_brand_grnorderproducthistory OWNER TO gramfac18;

--
-- Name: gram_to_brand_grnorderproducthistory_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_grnorderproducthistory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_grnorderproducthistory_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_grnorderproducthistory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_grnorderproducthistory_id_seq OWNED BY public.gram_to_brand_grnorderproducthistory.id;


--
-- Name: gram_to_brand_grnorderproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_grnorderproductmapping (
    id integer NOT NULL,
    po_product_quantity integer NOT NULL,
    po_product_price double precision NOT NULL,
    already_grned_product integer NOT NULL,
    product_invoice_price double precision NOT NULL,
    product_invoice_qty integer NOT NULL,
    manufacture_date date,
    expiry_date date,
    available_qty integer NOT NULL,
    ordered_qty integer NOT NULL,
    delivered_qty integer NOT NULL,
    returned_qty integer NOT NULL,
    damaged_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    grn_order_id integer,
    last_modified_by_id integer,
    product_id integer,
    CONSTRAINT gram_to_brand_grnorderproductmappin_already_grned_product_check CHECK ((already_grned_product >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_available_qty_check CHECK ((available_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_damaged_qty_check CHECK ((damaged_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_delivered_qty_check CHECK ((delivered_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_ordered_qty_check CHECK ((ordered_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_po_product_quantity_check CHECK ((po_product_quantity >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_product_invoice_qty_check CHECK ((product_invoice_qty >= 0)),
    CONSTRAINT gram_to_brand_grnorderproductmapping_returned_qty_check CHECK ((returned_qty >= 0))
);


ALTER TABLE public.gram_to_brand_grnorderproductmapping OWNER TO gramfac18;

--
-- Name: gram_to_brand_grnorderproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_grnorderproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_grnorderproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_grnorderproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_grnorderproductmapping_id_seq OWNED BY public.gram_to_brand_grnorderproductmapping.id;


--
-- Name: gram_to_brand_order; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_order (
    id integer NOT NULL,
    order_no character varying(255),
    total_mrp double precision NOT NULL,
    total_discount_amount double precision NOT NULL,
    total_tax_amount double precision NOT NULL,
    total_final_amount double precision NOT NULL,
    order_status character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    billing_address_id integer,
    last_modified_by_id integer,
    ordered_by_id integer,
    ordered_cart_id integer NOT NULL,
    received_by_id integer,
    shipping_address_id integer,
    shop_id integer
);


ALTER TABLE public.gram_to_brand_order OWNER TO gramfac18;

--
-- Name: gram_to_brand_order_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_order_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_order_id_seq OWNED BY public.gram_to_brand_order.id;


--
-- Name: gram_to_brand_orderedproductreserved; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_orderedproductreserved (
    id integer NOT NULL,
    reserved_qty integer NOT NULL,
    order_reserve_end_time timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    reserve_status character varying(100) NOT NULL,
    cart_id integer,
    order_product_reserved_id integer,
    product_id integer,
    CONSTRAINT gram_to_brand_orderedproductreserved_reserved_qty_check CHECK ((reserved_qty >= 0))
);


ALTER TABLE public.gram_to_brand_orderedproductreserved OWNER TO gramfac18;

--
-- Name: gram_to_brand_orderedproductreserved_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_orderedproductreserved_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_orderedproductreserved_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_orderedproductreserved_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_orderedproductreserved_id_seq OWNED BY public.gram_to_brand_orderedproductreserved.id;


--
-- Name: gram_to_brand_orderhistory; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_orderhistory (
    id integer NOT NULL,
    order_no character varying(255),
    total_mrp double precision NOT NULL,
    total_discount_amount double precision NOT NULL,
    total_tax_amount double precision NOT NULL,
    total_final_amount double precision NOT NULL,
    order_status character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    billing_address_id integer,
    buyer_shop_id integer,
    last_modified_by_id integer,
    ordered_by_id integer,
    ordered_cart_id integer NOT NULL,
    received_by_id integer,
    seller_shop_id integer,
    shipping_address_id integer
);


ALTER TABLE public.gram_to_brand_orderhistory OWNER TO gramfac18;

--
-- Name: gram_to_brand_orderhistory_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_orderhistory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_orderhistory_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_orderhistory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_orderhistory_id_seq OWNED BY public.gram_to_brand_orderhistory.id;


--
-- Name: gram_to_brand_orderitem; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_orderitem (
    id integer NOT NULL,
    ordered_qty integer NOT NULL,
    ordered_product_status character varying(50),
    ordered_price double precision NOT NULL,
    item_status character varying(255) NOT NULL,
    total_delivered_qty integer NOT NULL,
    total_returned_qty integer NOT NULL,
    total_damaged_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer NOT NULL,
    ordered_product_id integer NOT NULL,
    CONSTRAINT gram_to_brand_orderitem_ordered_qty_check CHECK ((ordered_qty >= 0)),
    CONSTRAINT gram_to_brand_orderitem_total_damaged_qty_check CHECK ((total_damaged_qty >= 0)),
    CONSTRAINT gram_to_brand_orderitem_total_delivered_qty_check CHECK ((total_delivered_qty >= 0)),
    CONSTRAINT gram_to_brand_orderitem_total_returned_qty_check CHECK ((total_returned_qty >= 0))
);


ALTER TABLE public.gram_to_brand_orderitem OWNER TO gramfac18;

--
-- Name: gram_to_brand_orderitem_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_orderitem_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_orderitem_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_orderitem_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_orderitem_id_seq OWNED BY public.gram_to_brand_orderitem.id;


--
-- Name: gram_to_brand_picklist; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_picklist (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    cart_id integer NOT NULL,
    order_id integer
);


ALTER TABLE public.gram_to_brand_picklist OWNER TO gramfac18;

--
-- Name: gram_to_brand_picklist_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_picklist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_picklist_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_picklist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_picklist_id_seq OWNED BY public.gram_to_brand_picklist.id;


--
-- Name: gram_to_brand_picklistitems; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_picklistitems (
    id integer NOT NULL,
    pick_qty integer NOT NULL,
    return_qty integer NOT NULL,
    damage_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    grn_order_id integer NOT NULL,
    pick_list_id integer NOT NULL,
    product_id integer,
    CONSTRAINT gram_to_brand_picklistitems_damage_qty_check CHECK ((damage_qty >= 0)),
    CONSTRAINT gram_to_brand_picklistitems_pick_qty_check CHECK ((pick_qty >= 0)),
    CONSTRAINT gram_to_brand_picklistitems_return_qty_check CHECK ((return_qty >= 0))
);


ALTER TABLE public.gram_to_brand_picklistitems OWNER TO gramfac18;

--
-- Name: gram_to_brand_picklistitems_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_picklistitems_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_picklistitems_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_picklistitems_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_picklistitems_id_seq OWNED BY public.gram_to_brand_picklistitems.id;


--
-- Name: gram_to_brand_po_message; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.gram_to_brand_po_message (
    id integer NOT NULL,
    message text,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    created_by_id integer
);


ALTER TABLE public.gram_to_brand_po_message OWNER TO gramfac18;

--
-- Name: gram_to_brand_po_message_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.gram_to_brand_po_message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gram_to_brand_po_message_id_seq OWNER TO gramfac18;

--
-- Name: gram_to_brand_po_message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.gram_to_brand_po_message_id_seq OWNED BY public.gram_to_brand_po_message.id;


--
-- Name: otp_phoneotp; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.otp_phoneotp (
    id integer NOT NULL,
    phone_number character varying(10) NOT NULL,
    otp character varying(10) NOT NULL,
    is_verified boolean NOT NULL,
    attempts integer NOT NULL,
    expires_in integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    last_otp timestamp with time zone NOT NULL,
    resend_in integer NOT NULL
);


ALTER TABLE public.otp_phoneotp OWNER TO gramfac18;

--
-- Name: otp_phoneotp_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.otp_phoneotp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.otp_phoneotp_id_seq OWNER TO gramfac18;

--
-- Name: otp_phoneotp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.otp_phoneotp_id_seq OWNED BY public.otp_phoneotp.id;


--
-- Name: products_color; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_color (
    id integer NOT NULL,
    color_name character varying(255) NOT NULL,
    color_code character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_color OWNER TO gramfac18;

--
-- Name: products_color_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_color_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_color_id_seq OWNER TO gramfac18;

--
-- Name: products_color_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_color_id_seq OWNED BY public.products_color.id;


--
-- Name: products_flavor; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_flavor (
    id integer NOT NULL,
    flavor_name character varying(255) NOT NULL,
    flavor_code character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_flavor OWNER TO gramfac18;

--
-- Name: products_flavor_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_flavor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_flavor_id_seq OWNER TO gramfac18;

--
-- Name: products_flavor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_flavor_id_seq OWNED BY public.products_flavor.id;


--
-- Name: products_fragrance; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_fragrance (
    id integer NOT NULL,
    fragrance_name character varying(255) NOT NULL,
    fragrance_code character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_fragrance OWNER TO gramfac18;

--
-- Name: products_fragrance_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_fragrance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_fragrance_id_seq OWNER TO gramfac18;

--
-- Name: products_fragrance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_fragrance_id_seq OWNED BY public.products_fragrance.id;


--
-- Name: products_packagesize; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_packagesize (
    id integer NOT NULL,
    pack_size_value character varying(255),
    pack_size_unit character varying(255) NOT NULL,
    pack_size_name character varying(50) NOT NULL,
    pack_length character varying(255),
    pack_width character varying(255),
    pack_height character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_packagesize OWNER TO gramfac18;

--
-- Name: products_packagesize_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_packagesize_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_packagesize_id_seq OWNER TO gramfac18;

--
-- Name: products_packagesize_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_packagesize_id_seq OWNED BY public.products_packagesize.id;


--
-- Name: products_product; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_product (
    id integer NOT NULL,
    product_name character varying(255) NOT NULL,
    product_slug character varying(255) NOT NULL,
    product_short_description character varying(255),
    product_long_description text,
    product_sku character varying(255) NOT NULL,
    product_gf_code character varying(255) NOT NULL,
    product_ean_code character varying(255) NOT NULL,
    product_inner_case_size character varying(255) NOT NULL,
    product_case_size character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    product_brand_id integer NOT NULL
);


ALTER TABLE public.products_product OWNER TO gramfac18;

--
-- Name: products_product_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_product_id_seq OWNER TO gramfac18;

--
-- Name: products_product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_product_id_seq OWNED BY public.products_product.id;


--
-- Name: products_productcategory; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productcategory (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    category_id integer NOT NULL,
    product_id integer NOT NULL
);


ALTER TABLE public.products_productcategory OWNER TO gramfac18;

--
-- Name: products_productcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productcategory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productcategory_id_seq OWNER TO gramfac18;

--
-- Name: products_productcategory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productcategory_id_seq OWNED BY public.products_productcategory.id;


--
-- Name: products_productcategoryhistory; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productcategoryhistory (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    category_id integer NOT NULL,
    product_id integer NOT NULL
);


ALTER TABLE public.products_productcategoryhistory OWNER TO gramfac18;

--
-- Name: products_productcategoryhistory_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productcategoryhistory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productcategoryhistory_id_seq OWNER TO gramfac18;

--
-- Name: products_productcategoryhistory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productcategoryhistory_id_seq OWNED BY public.products_productcategoryhistory.id;


--
-- Name: products_productcsv; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productcsv (
    id integer NOT NULL,
    file character varying(100) NOT NULL,
    uploaded_at timestamp with time zone NOT NULL
);


ALTER TABLE public.products_productcsv OWNER TO gramfac18;

--
-- Name: products_productcsv_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productcsv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productcsv_id_seq OWNER TO gramfac18;

--
-- Name: products_productcsv_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productcsv_id_seq OWNED BY public.products_productcsv.id;


--
-- Name: products_producthistory; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_producthistory (
    id integer NOT NULL,
    product_name character varying(255) NOT NULL,
    product_short_description character varying(255),
    product_long_description text,
    product_sku character varying(255),
    product_ean_code character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_producthistory OWNER TO gramfac18;

--
-- Name: products_producthistory_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_producthistory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_producthistory_id_seq OWNER TO gramfac18;

--
-- Name: products_producthistory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_producthistory_id_seq OWNED BY public.products_producthistory.id;


--
-- Name: products_productimage; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productimage (
    id integer NOT NULL,
    image_name character varying(255) NOT NULL,
    image_alt_text character varying(255),
    image character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    product_id integer NOT NULL
);


ALTER TABLE public.products_productimage OWNER TO gramfac18;

--
-- Name: products_productimage_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productimage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productimage_id_seq OWNER TO gramfac18;

--
-- Name: products_productimage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productimage_id_seq OWNED BY public.products_productimage.id;


--
-- Name: products_productoption; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productoption (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    color_id integer,
    flavor_id integer,
    fragrance_id integer,
    package_size_id integer,
    product_id integer NOT NULL,
    size_id integer,
    weight_id integer
);


ALTER TABLE public.products_productoption OWNER TO gramfac18;

--
-- Name: products_productoption_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productoption_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productoption_id_seq OWNER TO gramfac18;

--
-- Name: products_productoption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productoption_id_seq OWNED BY public.products_productoption.id;


--
-- Name: products_productprice; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productprice (
    id integer NOT NULL,
    mrp double precision,
    price_to_service_partner double precision,
    price_to_retailer double precision,
    price_to_super_retailer double precision,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    area_id integer,
    city_id integer,
    product_id integer NOT NULL,
    shop_id integer
);


ALTER TABLE public.products_productprice OWNER TO gramfac18;

--
-- Name: products_productprice_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productprice_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productprice_id_seq OWNER TO gramfac18;

--
-- Name: products_productprice_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productprice_id_seq OWNED BY public.products_productprice.id;


--
-- Name: products_productpricecsv; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productpricecsv (
    id integer NOT NULL,
    file character varying(100) NOT NULL,
    uploaded_at timestamp with time zone NOT NULL,
    area_id integer,
    city_id integer,
    country_id integer,
    states_id integer
);


ALTER TABLE public.products_productpricecsv OWNER TO gramfac18;

--
-- Name: products_productpricecsv_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productpricecsv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productpricecsv_id_seq OWNER TO gramfac18;

--
-- Name: products_productpricecsv_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productpricecsv_id_seq OWNED BY public.products_productpricecsv.id;


--
-- Name: products_productskugenerator; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productskugenerator (
    id integer NOT NULL,
    parent_cat_sku_code character varying(3) NOT NULL,
    cat_sku_code character varying(3) NOT NULL,
    brand_sku_code character varying(3) NOT NULL,
    last_auto_increment character varying(8) NOT NULL
);


ALTER TABLE public.products_productskugenerator OWNER TO gramfac18;

--
-- Name: products_productskugenerator_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productskugenerator_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productskugenerator_id_seq OWNER TO gramfac18;

--
-- Name: products_productskugenerator_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productskugenerator_id_seq OWNED BY public.products_productskugenerator.id;


--
-- Name: products_producttaxmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_producttaxmapping (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    product_id integer NOT NULL,
    tax_id integer NOT NULL
);


ALTER TABLE public.products_producttaxmapping OWNER TO gramfac18;

--
-- Name: products_producttaxmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_producttaxmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_producttaxmapping_id_seq OWNER TO gramfac18;

--
-- Name: products_producttaxmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_producttaxmapping_id_seq OWNED BY public.products_producttaxmapping.id;


--
-- Name: products_productvendormapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_productvendormapping (
    id integer NOT NULL,
    product_price double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    product_id integer NOT NULL,
    vendor_id integer NOT NULL
);


ALTER TABLE public.products_productvendormapping OWNER TO gramfac18;

--
-- Name: products_productvendormapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_productvendormapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_productvendormapping_id_seq OWNER TO gramfac18;

--
-- Name: products_productvendormapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_productvendormapping_id_seq OWNED BY public.products_productvendormapping.id;


--
-- Name: products_size; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_size (
    id integer NOT NULL,
    size_value character varying(255),
    size_unit character varying(255) NOT NULL,
    size_name character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_size OWNER TO gramfac18;

--
-- Name: products_size_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_size_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_size_id_seq OWNER TO gramfac18;

--
-- Name: products_size_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_size_id_seq OWNED BY public.products_size.id;


--
-- Name: products_tax; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_tax (
    id integer NOT NULL,
    tax_name character varying(255) NOT NULL,
    tax_type character varying(255),
    tax_percentage double precision NOT NULL,
    tax_start_at timestamp with time zone,
    tax_end_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_tax OWNER TO gramfac18;

--
-- Name: products_tax_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_tax_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_tax_id_seq OWNER TO gramfac18;

--
-- Name: products_tax_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_tax_id_seq OWNED BY public.products_tax.id;


--
-- Name: products_weight; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.products_weight (
    id integer NOT NULL,
    weight_value character varying(255),
    weight_unit character varying(255) NOT NULL,
    weight_name character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.products_weight OWNER TO gramfac18;

--
-- Name: products_weight_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.products_weight_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_weight_id_seq OWNER TO gramfac18;

--
-- Name: products_weight_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.products_weight_id_seq OWNED BY public.products_weight.id;


--
-- Name: retailer_to_gram_cart; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_cart (
    id integer NOT NULL,
    order_id character varying(255),
    cart_status character varying(200),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer
);


ALTER TABLE public.retailer_to_gram_cart OWNER TO gramfac18;

--
-- Name: retailer_to_gram_cart_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_cart_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_cart_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_cart_id_seq OWNED BY public.retailer_to_gram_cart.id;


--
-- Name: retailer_to_gram_cartproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_cartproductmapping (
    id integer NOT NULL,
    qty integer NOT NULL,
    qty_error_msg character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    cart_id integer NOT NULL,
    cart_product_id integer NOT NULL,
    CONSTRAINT retailer_to_gram_cartproductmapping_qty_check CHECK ((qty >= 0))
);


ALTER TABLE public.retailer_to_gram_cartproductmapping OWNER TO gramfac18;

--
-- Name: retailer_to_gram_cartproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_cartproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_cartproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_cartproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_cartproductmapping_id_seq OWNED BY public.retailer_to_gram_cartproductmapping.id;


--
-- Name: retailer_to_gram_customercare; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_customercare (
    id integer NOT NULL,
    name character varying(255),
    email_us character varying(200) NOT NULL,
    contact_us character varying(10) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    order_status character varying(20),
    select_issue character varying(100),
    complaint_detail character varying(2000),
    order_id_id integer
);


ALTER TABLE public.retailer_to_gram_customercare OWNER TO gramfac18;

--
-- Name: retailer_to_gram_customercare_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_customercare_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_customercare_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_customercare_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_customercare_id_seq OWNED BY public.retailer_to_gram_customercare.id;


--
-- Name: retailer_to_gram_note; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_note (
    id integer NOT NULL,
    note_type character varying(255) NOT NULL,
    amount double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer,
    ordered_product_id integer
);


ALTER TABLE public.retailer_to_gram_note OWNER TO gramfac18;

--
-- Name: retailer_to_gram_note_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_note_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_note_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_note_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_note_id_seq OWNED BY public.retailer_to_gram_note.id;


--
-- Name: retailer_to_gram_order; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_order (
    id integer NOT NULL,
    order_no character varying(255),
    total_mrp double precision NOT NULL,
    total_discount_amount double precision NOT NULL,
    total_tax_amount double precision NOT NULL,
    total_final_amount double precision NOT NULL,
    order_status character varying(50) NOT NULL,
    payment_mode character varying(255) NOT NULL,
    reference_no character varying(255),
    payment_amount double precision NOT NULL,
    payment_status character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    billing_address_id integer,
    buyer_shop_id integer,
    last_modified_by_id integer,
    ordered_by_id integer,
    ordered_cart_id integer NOT NULL,
    received_by_id integer,
    seller_shop_id integer,
    shipping_address_id integer
);


ALTER TABLE public.retailer_to_gram_order OWNER TO gramfac18;

--
-- Name: retailer_to_gram_order_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_order_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_order_id_seq OWNED BY public.retailer_to_gram_order.id;


--
-- Name: retailer_to_gram_orderedproduct; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_orderedproduct (
    id integer NOT NULL,
    invoice_no character varying(255),
    vehicle_no character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer,
    received_by_id integer,
    shipped_by_id integer
);


ALTER TABLE public.retailer_to_gram_orderedproduct OWNER TO gramfac18;

--
-- Name: retailer_to_gram_orderedproduct_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_orderedproduct_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_orderedproduct_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_orderedproduct_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_orderedproduct_id_seq OWNED BY public.retailer_to_gram_orderedproduct.id;


--
-- Name: retailer_to_gram_orderedproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_orderedproductmapping (
    id integer NOT NULL,
    shipped_qty integer NOT NULL,
    delivered_qty integer NOT NULL,
    returned_qty integer NOT NULL,
    damaged_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    ordered_product_id integer,
    product_id integer,
    CONSTRAINT retailer_to_gram_orderedproductmapping_damaged_qty_check CHECK ((damaged_qty >= 0)),
    CONSTRAINT retailer_to_gram_orderedproductmapping_delivered_qty_check CHECK ((delivered_qty >= 0)),
    CONSTRAINT retailer_to_gram_orderedproductmapping_returned_qty_check CHECK ((returned_qty >= 0)),
    CONSTRAINT retailer_to_gram_orderedproductmapping_shipped_qty_check CHECK ((shipped_qty >= 0))
);


ALTER TABLE public.retailer_to_gram_orderedproductmapping OWNER TO gramfac18;

--
-- Name: retailer_to_gram_orderedproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_orderedproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_orderedproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_orderedproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_orderedproductmapping_id_seq OWNED BY public.retailer_to_gram_orderedproductmapping.id;


--
-- Name: retailer_to_gram_payment; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_gram_payment (
    id integer NOT NULL,
    name character varying(255),
    paid_amount numeric(20,4) NOT NULL,
    payment_choice character varying(30),
    neft_reference_number character varying(20),
    payment_status character varying(50),
    order_id_id integer
);


ALTER TABLE public.retailer_to_gram_payment OWNER TO gramfac18;

--
-- Name: retailer_to_gram_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_gram_payment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_gram_payment_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_gram_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_gram_payment_id_seq OWNED BY public.retailer_to_gram_payment.id;


--
-- Name: retailer_to_sp_cart; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_cart (
    id integer NOT NULL,
    order_id character varying(255),
    cart_status character varying(200),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer
);


ALTER TABLE public.retailer_to_sp_cart OWNER TO gramfac18;

--
-- Name: retailer_to_sp_cart_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_cart_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_cart_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_cart_id_seq OWNED BY public.retailer_to_sp_cart.id;


--
-- Name: retailer_to_sp_cartproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_cartproductmapping (
    id integer NOT NULL,
    qty integer NOT NULL,
    qty_error_msg character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    cart_id integer NOT NULL,
    cart_product_id integer NOT NULL,
    CONSTRAINT retailer_to_sp_cartproductmapping_qty_check CHECK ((qty >= 0))
);


ALTER TABLE public.retailer_to_sp_cartproductmapping OWNER TO gramfac18;

--
-- Name: retailer_to_sp_cartproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_cartproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_cartproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_cartproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_cartproductmapping_id_seq OWNED BY public.retailer_to_sp_cartproductmapping.id;


--
-- Name: retailer_to_sp_customercare; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_customercare (
    id integer NOT NULL,
    name character varying(255),
    email_us character varying(200) NOT NULL,
    contact_us character varying(10) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    order_status character varying(20),
    select_issue character varying(100),
    complaint_detail character varying(2000),
    order_id_id integer
);


ALTER TABLE public.retailer_to_sp_customercare OWNER TO gramfac18;

--
-- Name: retailer_to_sp_customercare_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_customercare_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_customercare_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_customercare_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_customercare_id_seq OWNED BY public.retailer_to_sp_customercare.id;


--
-- Name: retailer_to_sp_note; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_note (
    id integer NOT NULL,
    note_type character varying(255) NOT NULL,
    amount double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer,
    ordered_product_id integer
);


ALTER TABLE public.retailer_to_sp_note OWNER TO gramfac18;

--
-- Name: retailer_to_sp_note_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_note_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_note_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_note_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_note_id_seq OWNED BY public.retailer_to_sp_note.id;


--
-- Name: retailer_to_sp_order; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_order (
    id integer NOT NULL,
    order_no character varying(255),
    total_mrp double precision NOT NULL,
    total_discount_amount double precision NOT NULL,
    total_tax_amount double precision NOT NULL,
    total_final_amount double precision NOT NULL,
    order_status character varying(50) NOT NULL,
    payment_mode character varying(255) NOT NULL,
    reference_no character varying(255),
    payment_amount double precision NOT NULL,
    payment_status character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    billing_address_id integer,
    buyer_shop_id integer,
    last_modified_by_id integer,
    ordered_by_id integer,
    ordered_cart_id integer NOT NULL,
    received_by_id integer,
    seller_shop_id integer,
    shipping_address_id integer
);


ALTER TABLE public.retailer_to_sp_order OWNER TO gramfac18;

--
-- Name: retailer_to_sp_order_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_order_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_order_id_seq OWNED BY public.retailer_to_sp_order.id;


--
-- Name: retailer_to_sp_orderedproduct; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_orderedproduct (
    id integer NOT NULL,
    invoice_no character varying(255),
    vehicle_no character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer,
    received_by_id integer,
    shipped_by_id integer
);


ALTER TABLE public.retailer_to_sp_orderedproduct OWNER TO gramfac18;

--
-- Name: retailer_to_sp_orderedproduct_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_orderedproduct_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_orderedproduct_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_orderedproduct_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_orderedproduct_id_seq OWNED BY public.retailer_to_sp_orderedproduct.id;


--
-- Name: retailer_to_sp_orderedproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_orderedproductmapping (
    id integer NOT NULL,
    shipped_qty integer NOT NULL,
    delivered_qty integer NOT NULL,
    returned_qty integer NOT NULL,
    damaged_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    ordered_product_id integer,
    product_id integer,
    CONSTRAINT retailer_to_sp_orderedproductmapping_damaged_qty_check CHECK ((damaged_qty >= 0)),
    CONSTRAINT retailer_to_sp_orderedproductmapping_delivered_qty_check CHECK ((delivered_qty >= 0)),
    CONSTRAINT retailer_to_sp_orderedproductmapping_returned_qty_check CHECK ((returned_qty >= 0)),
    CONSTRAINT retailer_to_sp_orderedproductmapping_shipped_qty_check CHECK ((shipped_qty >= 0))
);


ALTER TABLE public.retailer_to_sp_orderedproductmapping OWNER TO gramfac18;

--
-- Name: retailer_to_sp_orderedproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_orderedproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_orderedproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_orderedproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_orderedproductmapping_id_seq OWNED BY public.retailer_to_sp_orderedproductmapping.id;


--
-- Name: retailer_to_sp_payment; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.retailer_to_sp_payment (
    id integer NOT NULL,
    name character varying(255),
    paid_amount numeric(20,4) NOT NULL,
    payment_choice character varying(30),
    neft_reference_number character varying(20),
    payment_status character varying(50),
    order_id_id integer
);


ALTER TABLE public.retailer_to_sp_payment OWNER TO gramfac18;

--
-- Name: retailer_to_sp_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.retailer_to_sp_payment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.retailer_to_sp_payment_id_seq OWNER TO gramfac18;

--
-- Name: retailer_to_sp_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.retailer_to_sp_payment_id_seq OWNED BY public.retailer_to_sp_payment.id;


--
-- Name: shops_parentretailermapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_parentretailermapping (
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    parent_id integer NOT NULL,
    retailer_id integer NOT NULL
);


ALTER TABLE public.shops_parentretailermapping OWNER TO gramfac18;

--
-- Name: shops_parentretailermapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_parentretailermapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_parentretailermapping_id_seq OWNER TO gramfac18;

--
-- Name: shops_parentretailermapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_parentretailermapping_id_seq OWNED BY public.shops_parentretailermapping.id;


--
-- Name: shops_retailertype; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_retailertype (
    id integer NOT NULL,
    retailer_type_name character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL
);


ALTER TABLE public.shops_retailertype OWNER TO gramfac18;

--
-- Name: shops_retailertype_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_retailertype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_retailertype_id_seq OWNER TO gramfac18;

--
-- Name: shops_retailertype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_retailertype_id_seq OWNED BY public.shops_retailertype.id;


--
-- Name: shops_shop; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_shop (
    id integer NOT NULL,
    shop_name character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    shop_owner_id integer NOT NULL,
    shop_type_id integer NOT NULL
);


ALTER TABLE public.shops_shop OWNER TO gramfac18;

--
-- Name: shops_shop_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_shop_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_shop_id_seq OWNER TO gramfac18;

--
-- Name: shops_shop_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_shop_id_seq OWNED BY public.shops_shop.id;


--
-- Name: shops_shop_related_users; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_shop_related_users (
    id integer NOT NULL,
    shop_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.shops_shop_related_users OWNER TO gramfac18;

--
-- Name: shops_shop_related_users_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_shop_related_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_shop_related_users_id_seq OWNER TO gramfac18;

--
-- Name: shops_shop_related_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_shop_related_users_id_seq OWNED BY public.shops_shop_related_users.id;


--
-- Name: shops_shopdocument; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_shopdocument (
    id integer NOT NULL,
    shop_document_type character varying(100) NOT NULL,
    shop_document_number character varying(100) NOT NULL,
    shop_document_photo character varying(100) NOT NULL,
    shop_name_id integer NOT NULL
);


ALTER TABLE public.shops_shopdocument OWNER TO gramfac18;

--
-- Name: shops_shopdocument_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_shopdocument_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_shopdocument_id_seq OWNER TO gramfac18;

--
-- Name: shops_shopdocument_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_shopdocument_id_seq OWNED BY public.shops_shopdocument.id;


--
-- Name: shops_shopphoto; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_shopphoto (
    id integer NOT NULL,
    shop_photo character varying(100) NOT NULL,
    shop_name_id integer NOT NULL
);


ALTER TABLE public.shops_shopphoto OWNER TO gramfac18;

--
-- Name: shops_shopphoto_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_shopphoto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_shopphoto_id_seq OWNER TO gramfac18;

--
-- Name: shops_shopphoto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_shopphoto_id_seq OWNED BY public.shops_shopphoto.id;


--
-- Name: shops_shoptype; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.shops_shoptype (
    id integer NOT NULL,
    shop_type character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    status boolean NOT NULL,
    shop_sub_type_id integer
);


ALTER TABLE public.shops_shoptype OWNER TO gramfac18;

--
-- Name: shops_shoptype_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.shops_shoptype_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shops_shoptype_id_seq OWNER TO gramfac18;

--
-- Name: shops_shoptype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.shops_shoptype_id_seq OWNED BY public.shops_shoptype.id;


--
-- Name: sp_to_gram_cart; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_cart (
    id integer NOT NULL,
    po_no character varying(255),
    po_status character varying(200),
    po_creation_date date NOT NULL,
    po_validity_date date NOT NULL,
    payment_term text,
    delivery_term text,
    po_amount double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    po_raised_by_id integer,
    shop_id integer
);


ALTER TABLE public.sp_to_gram_cart OWNER TO gramfac18;

--
-- Name: sp_to_gram_cart_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_cart_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_cart_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_cart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_cart_id_seq OWNED BY public.sp_to_gram_cart.id;


--
-- Name: sp_to_gram_cartproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_cartproductmapping (
    id integer NOT NULL,
    case_size integer NOT NULL,
    number_of_cases integer NOT NULL,
    qty integer NOT NULL,
    scheme double precision,
    price double precision NOT NULL,
    total_price integer NOT NULL,
    cart_id integer NOT NULL,
    cart_product_id integer NOT NULL,
    CONSTRAINT sp_to_gram_cartproductmapping_case_size_check CHECK ((case_size >= 0)),
    CONSTRAINT sp_to_gram_cartproductmapping_number_of_cases_check CHECK ((number_of_cases >= 0)),
    CONSTRAINT sp_to_gram_cartproductmapping_qty_check CHECK ((qty >= 0)),
    CONSTRAINT sp_to_gram_cartproductmapping_total_price_check CHECK ((total_price >= 0))
);


ALTER TABLE public.sp_to_gram_cartproductmapping OWNER TO gramfac18;

--
-- Name: sp_to_gram_cartproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_cartproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_cartproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_cartproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_cartproductmapping_id_seq OWNED BY public.sp_to_gram_cartproductmapping.id;


--
-- Name: sp_to_gram_order; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_order (
    id integer NOT NULL,
    order_no character varying(255),
    total_mrp double precision NOT NULL,
    total_discount_amount double precision NOT NULL,
    total_tax_amount double precision NOT NULL,
    total_final_amount double precision NOT NULL,
    order_status character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    billing_address_id integer,
    last_modified_by_id integer,
    ordered_by_id integer,
    ordered_cart_id integer NOT NULL,
    received_by_id integer,
    shipping_address_id integer
);


ALTER TABLE public.sp_to_gram_order OWNER TO gramfac18;

--
-- Name: sp_to_gram_order_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_order_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_order_id_seq OWNED BY public.sp_to_gram_order.id;


--
-- Name: sp_to_gram_orderedproduct; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_orderedproduct (
    id integer NOT NULL,
    invoice_no character varying(255),
    vehicle_no character varying(255),
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    order_id integer,
    received_by_id integer,
    shipped_by_id integer
);


ALTER TABLE public.sp_to_gram_orderedproduct OWNER TO gramfac18;

--
-- Name: sp_to_gram_orderedproduct_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_orderedproduct_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_orderedproduct_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_orderedproduct_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_orderedproduct_id_seq OWNED BY public.sp_to_gram_orderedproduct.id;


--
-- Name: sp_to_gram_orderedproductmapping; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_orderedproductmapping (
    id integer NOT NULL,
    manufacture_date date,
    expiry_date date,
    shipped_qty integer NOT NULL,
    available_qty integer NOT NULL,
    ordered_qty integer NOT NULL,
    delivered_qty integer NOT NULL,
    returned_qty integer NOT NULL,
    damaged_qty integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    last_modified_by_id integer,
    ordered_product_id integer,
    product_id integer,
    CONSTRAINT sp_to_gram_orderedproductmapping_available_qty_check CHECK ((available_qty >= 0)),
    CONSTRAINT sp_to_gram_orderedproductmapping_damaged_qty_check CHECK ((damaged_qty >= 0)),
    CONSTRAINT sp_to_gram_orderedproductmapping_delivered_qty_check CHECK ((delivered_qty >= 0)),
    CONSTRAINT sp_to_gram_orderedproductmapping_ordered_qty_check CHECK ((ordered_qty >= 0)),
    CONSTRAINT sp_to_gram_orderedproductmapping_returned_qty_check CHECK ((returned_qty >= 0)),
    CONSTRAINT sp_to_gram_orderedproductmapping_shipped_qty_check CHECK ((shipped_qty >= 0))
);


ALTER TABLE public.sp_to_gram_orderedproductmapping OWNER TO gramfac18;

--
-- Name: sp_to_gram_orderedproductmapping_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_orderedproductmapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_orderedproductmapping_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_orderedproductmapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_orderedproductmapping_id_seq OWNED BY public.sp_to_gram_orderedproductmapping.id;


--
-- Name: sp_to_gram_orderedproductreserved; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_orderedproductreserved (
    id integer NOT NULL,
    reserved_qty integer NOT NULL,
    order_reserve_end_time timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    cart_id integer,
    order_product_reserved_id integer,
    product_id integer,
    reserve_status character varying(100) NOT NULL,
    CONSTRAINT sp_to_gram_orderedproductreserved_reserved_qty_check CHECK ((reserved_qty >= 0))
);


ALTER TABLE public.sp_to_gram_orderedproductreserved OWNER TO gramfac18;

--
-- Name: sp_to_gram_orderedproductreserved_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_orderedproductreserved_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_orderedproductreserved_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_orderedproductreserved_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_orderedproductreserved_id_seq OWNED BY public.sp_to_gram_orderedproductreserved.id;


--
-- Name: sp_to_gram_spnote; Type: TABLE; Schema: public; Owner: gramfac18
--

CREATE TABLE public.sp_to_gram_spnote (
    id integer NOT NULL,
    brand_note_id character varying(255),
    note_type character varying(255) NOT NULL,
    amount double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at timestamp with time zone NOT NULL,
    grn_order_id integer,
    last_modified_by_id integer,
    order_id integer
);


ALTER TABLE public.sp_to_gram_spnote OWNER TO gramfac18;

--
-- Name: sp_to_gram_spnote_id_seq; Type: SEQUENCE; Schema: public; Owner: gramfac18
--

CREATE SEQUENCE public.sp_to_gram_spnote_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sp_to_gram_spnote_id_seq OWNER TO gramfac18;

--
-- Name: sp_to_gram_spnote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gramfac18
--

ALTER SEQUENCE public.sp_to_gram_spnote_id_seq OWNED BY public.sp_to_gram_spnote.id;


--
-- Name: account_emailaddress id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailaddress ALTER COLUMN id SET DEFAULT nextval('public.account_emailaddress_id_seq'::regclass);


--
-- Name: account_emailconfirmation id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailconfirmation ALTER COLUMN id SET DEFAULT nextval('public.account_emailconfirmation_id_seq'::regclass);


--
-- Name: accounts_user id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user ALTER COLUMN id SET DEFAULT nextval('public.accounts_user_id_seq'::regclass);


--
-- Name: accounts_user_groups id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_groups ALTER COLUMN id SET DEFAULT nextval('public.accounts_user_groups_id_seq'::regclass);


--
-- Name: accounts_user_user_permissions id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('public.accounts_user_user_permissions_id_seq'::regclass);


--
-- Name: accounts_userdocument id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_userdocument ALTER COLUMN id SET DEFAULT nextval('public.accounts_userdocument_id_seq'::regclass);


--
-- Name: addresses_address id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_address ALTER COLUMN id SET DEFAULT nextval('public.addresses_address_id_seq'::regclass);


--
-- Name: addresses_area id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_area ALTER COLUMN id SET DEFAULT nextval('public.addresses_area_id_seq'::regclass);


--
-- Name: addresses_city id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_city ALTER COLUMN id SET DEFAULT nextval('public.addresses_city_id_seq'::regclass);


--
-- Name: addresses_country id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_country ALTER COLUMN id SET DEFAULT nextval('public.addresses_country_id_seq'::regclass);


--
-- Name: addresses_invoicecitymapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_invoicecitymapping ALTER COLUMN id SET DEFAULT nextval('public.addresses_invoicecitymapping_id_seq'::regclass);


--
-- Name: addresses_state id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_state ALTER COLUMN id SET DEFAULT nextval('public.addresses_state_id_seq'::regclass);


--
-- Name: allauth_socialaccount id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialaccount ALTER COLUMN id SET DEFAULT nextval('public.allauth_socialaccount_id_seq'::regclass);


--
-- Name: allauth_socialapp id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp ALTER COLUMN id SET DEFAULT nextval('public.allauth_socialapp_id_seq'::regclass);


--
-- Name: allauth_socialapp_sites id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp_sites ALTER COLUMN id SET DEFAULT nextval('public.allauth_socialapp_sites_id_seq'::regclass);


--
-- Name: allauth_socialtoken id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialtoken ALTER COLUMN id SET DEFAULT nextval('public.allauth_socialtoken_id_seq'::regclass);


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- Name: auth_group_permissions id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('public.auth_group_permissions_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- Name: banner_banner id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_banner ALTER COLUMN id SET DEFAULT nextval('public.banner_banner_id_seq'::regclass);


--
-- Name: banner_bannerdata id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerdata ALTER COLUMN id SET DEFAULT nextval('public.banner_bannerdata_id_seq'::regclass);


--
-- Name: banner_bannerposition id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerposition ALTER COLUMN id SET DEFAULT nextval('public.banner_bannerposition_id_seq'::regclass);


--
-- Name: banner_bannerslot id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerslot ALTER COLUMN id SET DEFAULT nextval('public.banner_bannerslot_id_seq'::regclass);


--
-- Name: banner_page id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_page ALTER COLUMN id SET DEFAULT nextval('public.banner_page_id_seq'::regclass);


--
-- Name: brand_brand id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_brand ALTER COLUMN id SET DEFAULT nextval('public.brand_brand_id_seq'::regclass);


--
-- Name: brand_branddata id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_branddata ALTER COLUMN id SET DEFAULT nextval('public.brand_branddata_id_seq'::regclass);


--
-- Name: brand_brandposition id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_brandposition ALTER COLUMN id SET DEFAULT nextval('public.brand_brandposition_id_seq'::regclass);


--
-- Name: brand_vendor id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_vendor ALTER COLUMN id SET DEFAULT nextval('public.brand_vendor_id_seq'::regclass);


--
-- Name: categories_category id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category ALTER COLUMN id SET DEFAULT nextval('public.categories_category_id_seq'::regclass);


--
-- Name: categories_categorydata id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_categorydata ALTER COLUMN id SET DEFAULT nextval('public.categories_categorydata_id_seq'::regclass);


--
-- Name: categories_categoryposation id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_categoryposation ALTER COLUMN id SET DEFAULT nextval('public.categories_categoryposation_id_seq'::regclass);


--
-- Name: django_admin_log id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_admin_log ALTER COLUMN id SET DEFAULT nextval('public.django_admin_log_id_seq'::regclass);


--
-- Name: django_content_type id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_content_type ALTER COLUMN id SET DEFAULT nextval('public.django_content_type_id_seq'::regclass);


--
-- Name: django_migrations id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_migrations ALTER COLUMN id SET DEFAULT nextval('public.django_migrations_id_seq'::regclass);


--
-- Name: django_site id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_site ALTER COLUMN id SET DEFAULT nextval('public.django_site_id_seq'::regclass);


--
-- Name: gram_to_brand_brandnote id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_brandnote ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_brandnote_id_seq'::regclass);


--
-- Name: gram_to_brand_cart id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_cart_id_seq'::regclass);


--
-- Name: gram_to_brand_cartproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cartproductmapping ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_cartproductmapping_id_seq'::regclass);


--
-- Name: gram_to_brand_grnorder id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorder ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_grnorder_id_seq'::regclass);


--
-- Name: gram_to_brand_grnorderproducthistory id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_grnorderproducthistory_id_seq'::regclass);


--
-- Name: gram_to_brand_grnorderproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproductmapping ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_grnorderproductmapping_id_seq'::regclass);


--
-- Name: gram_to_brand_order id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_order_id_seq'::regclass);


--
-- Name: gram_to_brand_orderedproductreserved id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderedproductreserved ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_orderedproductreserved_id_seq'::regclass);


--
-- Name: gram_to_brand_orderhistory id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_orderhistory_id_seq'::regclass);


--
-- Name: gram_to_brand_orderitem id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderitem ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_orderitem_id_seq'::regclass);


--
-- Name: gram_to_brand_picklist id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklist ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_picklist_id_seq'::regclass);


--
-- Name: gram_to_brand_picklistitems id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklistitems ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_picklistitems_id_seq'::regclass);


--
-- Name: gram_to_brand_po_message id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_po_message ALTER COLUMN id SET DEFAULT nextval('public.gram_to_brand_po_message_id_seq'::regclass);


--
-- Name: otp_phoneotp id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.otp_phoneotp ALTER COLUMN id SET DEFAULT nextval('public.otp_phoneotp_id_seq'::regclass);


--
-- Name: products_color id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_color ALTER COLUMN id SET DEFAULT nextval('public.products_color_id_seq'::regclass);


--
-- Name: products_flavor id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_flavor ALTER COLUMN id SET DEFAULT nextval('public.products_flavor_id_seq'::regclass);


--
-- Name: products_fragrance id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_fragrance ALTER COLUMN id SET DEFAULT nextval('public.products_fragrance_id_seq'::regclass);


--
-- Name: products_packagesize id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_packagesize ALTER COLUMN id SET DEFAULT nextval('public.products_packagesize_id_seq'::regclass);


--
-- Name: products_product id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_product ALTER COLUMN id SET DEFAULT nextval('public.products_product_id_seq'::regclass);


--
-- Name: products_productcategory id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategory ALTER COLUMN id SET DEFAULT nextval('public.products_productcategory_id_seq'::regclass);


--
-- Name: products_productcategoryhistory id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategoryhistory ALTER COLUMN id SET DEFAULT nextval('public.products_productcategoryhistory_id_seq'::regclass);


--
-- Name: products_productcsv id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcsv ALTER COLUMN id SET DEFAULT nextval('public.products_productcsv_id_seq'::regclass);


--
-- Name: products_producthistory id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_producthistory ALTER COLUMN id SET DEFAULT nextval('public.products_producthistory_id_seq'::regclass);


--
-- Name: products_productimage id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productimage ALTER COLUMN id SET DEFAULT nextval('public.products_productimage_id_seq'::regclass);


--
-- Name: products_productoption id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption ALTER COLUMN id SET DEFAULT nextval('public.products_productoption_id_seq'::regclass);


--
-- Name: products_productprice id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productprice ALTER COLUMN id SET DEFAULT nextval('public.products_productprice_id_seq'::regclass);


--
-- Name: products_productpricecsv id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productpricecsv ALTER COLUMN id SET DEFAULT nextval('public.products_productpricecsv_id_seq'::regclass);


--
-- Name: products_productskugenerator id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productskugenerator ALTER COLUMN id SET DEFAULT nextval('public.products_productskugenerator_id_seq'::regclass);


--
-- Name: products_producttaxmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_producttaxmapping ALTER COLUMN id SET DEFAULT nextval('public.products_producttaxmapping_id_seq'::regclass);


--
-- Name: products_productvendormapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productvendormapping ALTER COLUMN id SET DEFAULT nextval('public.products_productvendormapping_id_seq'::regclass);


--
-- Name: products_size id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_size ALTER COLUMN id SET DEFAULT nextval('public.products_size_id_seq'::regclass);


--
-- Name: products_tax id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_tax ALTER COLUMN id SET DEFAULT nextval('public.products_tax_id_seq'::regclass);


--
-- Name: products_weight id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_weight ALTER COLUMN id SET DEFAULT nextval('public.products_weight_id_seq'::regclass);


--
-- Name: retailer_to_gram_cart id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cart ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_cart_id_seq'::regclass);


--
-- Name: retailer_to_gram_cartproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cartproductmapping ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_cartproductmapping_id_seq'::regclass);


--
-- Name: retailer_to_gram_customercare id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_customercare ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_customercare_id_seq'::regclass);


--
-- Name: retailer_to_gram_note id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_note ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_note_id_seq'::regclass);


--
-- Name: retailer_to_gram_order id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_order_id_seq'::regclass);


--
-- Name: retailer_to_gram_orderedproduct id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproduct ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_orderedproduct_id_seq'::regclass);


--
-- Name: retailer_to_gram_orderedproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproductmapping ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_orderedproductmapping_id_seq'::regclass);


--
-- Name: retailer_to_gram_payment id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_payment ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_gram_payment_id_seq'::regclass);


--
-- Name: retailer_to_sp_cart id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cart ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_cart_id_seq'::regclass);


--
-- Name: retailer_to_sp_cartproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cartproductmapping ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_cartproductmapping_id_seq'::regclass);


--
-- Name: retailer_to_sp_customercare id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_customercare ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_customercare_id_seq'::regclass);


--
-- Name: retailer_to_sp_note id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_note ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_note_id_seq'::regclass);


--
-- Name: retailer_to_sp_order id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_order_id_seq'::regclass);


--
-- Name: retailer_to_sp_orderedproduct id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproduct ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_orderedproduct_id_seq'::regclass);


--
-- Name: retailer_to_sp_orderedproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproductmapping ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_orderedproductmapping_id_seq'::regclass);


--
-- Name: retailer_to_sp_payment id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_payment ALTER COLUMN id SET DEFAULT nextval('public.retailer_to_sp_payment_id_seq'::regclass);


--
-- Name: shops_parentretailermapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_parentretailermapping ALTER COLUMN id SET DEFAULT nextval('public.shops_parentretailermapping_id_seq'::regclass);


--
-- Name: shops_retailertype id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_retailertype ALTER COLUMN id SET DEFAULT nextval('public.shops_retailertype_id_seq'::regclass);


--
-- Name: shops_shop id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop ALTER COLUMN id SET DEFAULT nextval('public.shops_shop_id_seq'::regclass);


--
-- Name: shops_shop_related_users id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop_related_users ALTER COLUMN id SET DEFAULT nextval('public.shops_shop_related_users_id_seq'::regclass);


--
-- Name: shops_shopdocument id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shopdocument ALTER COLUMN id SET DEFAULT nextval('public.shops_shopdocument_id_seq'::regclass);


--
-- Name: shops_shopphoto id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shopphoto ALTER COLUMN id SET DEFAULT nextval('public.shops_shopphoto_id_seq'::regclass);


--
-- Name: shops_shoptype id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shoptype ALTER COLUMN id SET DEFAULT nextval('public.shops_shoptype_id_seq'::regclass);


--
-- Name: sp_to_gram_cart id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cart ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_cart_id_seq'::regclass);


--
-- Name: sp_to_gram_cartproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cartproductmapping ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_cartproductmapping_id_seq'::regclass);


--
-- Name: sp_to_gram_order id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_order_id_seq'::regclass);


--
-- Name: sp_to_gram_orderedproduct id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproduct ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_orderedproduct_id_seq'::regclass);


--
-- Name: sp_to_gram_orderedproductmapping id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductmapping ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_orderedproductmapping_id_seq'::regclass);


--
-- Name: sp_to_gram_orderedproductreserved id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductreserved ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_orderedproductreserved_id_seq'::regclass);


--
-- Name: sp_to_gram_spnote id; Type: DEFAULT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_spnote ALTER COLUMN id SET DEFAULT nextval('public.sp_to_gram_spnote_id_seq'::regclass);


--
-- Data for Name: account_emailaddress; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.account_emailaddress (id, email, verified, "primary", user_id) FROM stdin;
2	prajapat.mayank@gmail.com	f	t	8
3	pallavi@gramfactory.com	f	t	9
4	nikita@gramfactory.com	f	t	10
5	har@gmail.com	f	t	13
\.


--
-- Data for Name: account_emailconfirmation; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.account_emailconfirmation (id, created, sent, key, email_address_id) FROM stdin;
\.


--
-- Data for Name: accounts_user; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.accounts_user (id, password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, phone_number, email, user_photo, user_type) FROM stdin;
12	pbkdf2_sha256$120000$CqUwEayVcPJo$hViQ1b3K10uv7kh2Dc7ebhNaERPmKaiFu+O+ZhYURWk=	\N	f			f	t	2019-01-09 10:53:33.89508+00	9582288240	anil@gramfactory.com		6
8	pbkdf2_sha256$120000$8pj9OmXiFDtz$JfBV0UPxmPbQ2HuhlR/yTC4Qe+ExjN24Lnf89pKgQwo=	2019-01-09 11:41:52.626705+00	f	Mayank	Prajapat	f	t	2019-01-09 06:21:00.332905+00	9899746673	prajapat.mayank@gmail.com		6
13	pbkdf2_sha256$120000$4cI5M4s0CBCw$ad+fXFtkwNp1bD/AQTOiYqnmYHYIa+frpltXz95VZus=	2019-01-09 11:55:10.774181+00	f	harmeek	Singh	f	t	2019-01-09 11:55:10.558684+00	7042545165	har@gmail.com		6
7	pbkdf2_sha256$120000$NMKOiLziF245$HDuAGMIP0aENnuRKArjrfSJctsfsm6/7zRL5VdS4ShE=	2019-01-10 08:07:54.541791+00	t	GAURAV	SINGH	t	t	2019-01-08 12:49:06.282092+00	7006440794	gaurav@gramfactory.com		6
4	pbkdf2_sha256$120000$6EQQzpCaeZy7$DC5kQVPGs99NW4BNhkrcPlj9t+DfkMmn8AtSj1/D50s=	\N	t	Jagjeet	Singh	f	t	2019-01-08 06:40:25.118623+00	8567075678	jagjeet@gramfactory.com		1
6	pbkdf2_sha256$120000$NLhI8KV4Qrih$0RVXkrh5H2cYJ7xIwXHPGr51u1gMo4ORyQodvHvmphg=	2019-01-08 12:36:52.632334+00	f	kshitij		f	t	2019-01-08 12:36:52.468393+00	9560237858			6
2	pbkdf2_sha256$120000$4xXvLkor8Mkn$PY7aUGEc4IThoopPr4r4yRpR65xpRTuayoND3AMBOZE=	2019-01-09 04:22:29.648537+00	t	Madhav	Kumar	t	t	2019-01-07 16:36:59.550149+00	8750858087	admin@gramfactory.com		6
9	pbkdf2_sha256$120000$dXOTFsdCUQd1$7VHGoXpOppHa2XLMfRoWPu7d1QtB7uMjb4zl6oAb8Oo=	2019-01-09 07:09:37.015694+00	t	Pallavi	Chouhan	t	t	2019-01-09 07:09:36.841412+00	7763886418	pallavi@gramfactory.com		6
1	pbkdf2_sha256$120000$YThl7QXt7iEJ$qEyFM81weYQS1Qzc7q0bOe0cnenh0tCAlWRiEzoWODI=	2019-01-09 07:25:25.098708+00	t	Mukesh	Kumar	t	t	2019-01-07 12:28:54.1147+00	9911703645	admin@gmail.com		6
10	pbkdf2_sha256$120000$aDJgQB263RuS$ezIt+EUhQTrKXeS0uLabdS0pGje5vnzdwNaB7KoWcQs=	2019-01-09 08:00:52.443233+00	f	Nikita	upreti	f	t	2019-01-09 08:00:52.217206+00	9999682701	nikita@gramfactory.com		6
11	pbkdf2_sha256$120000$ZHr66BWDJak1$7mT8D9I3lmWXNPdk8VvAa+sopxcIjWmf9wJ+fb4iDoE=	2019-01-09 09:51:51.547901+00	f			t	t	2019-01-09 09:46:30.622824+00	9555072423			6
\.


--
-- Data for Name: accounts_user_groups; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.accounts_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: accounts_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.accounts_user_user_permissions (id, user_id, permission_id) FROM stdin;
1	11	1
2	11	2
3	11	3
4	11	4
5	11	5
6	11	6
7	11	7
8	11	8
9	11	9
10	11	10
11	11	11
12	11	12
13	11	13
14	11	14
15	11	15
16	11	16
17	11	17
18	11	18
19	11	19
20	11	20
21	11	21
22	11	22
23	11	23
24	11	24
25	11	25
26	11	26
27	11	27
28	11	28
29	11	29
30	11	30
31	11	31
32	11	32
33	11	33
34	11	34
35	11	35
36	11	36
37	11	37
38	11	38
39	11	39
40	11	40
41	11	41
42	11	42
43	11	43
44	11	44
45	11	45
46	11	46
47	11	47
48	11	48
49	11	49
50	11	50
51	11	51
52	11	52
53	11	53
54	11	54
55	11	55
56	11	56
57	11	57
58	11	58
59	11	59
60	11	60
61	11	61
62	11	62
63	11	63
64	11	64
65	11	65
66	11	66
67	11	67
68	11	68
69	11	69
70	11	70
71	11	71
72	11	72
73	11	73
74	11	74
75	11	75
76	11	76
77	11	77
78	11	78
79	11	79
80	11	80
81	11	81
82	11	82
83	11	83
84	11	84
85	11	85
86	11	86
87	11	87
88	11	88
89	11	89
90	11	90
91	11	91
92	11	92
93	11	93
94	11	94
95	11	95
96	11	96
97	11	97
98	11	98
99	11	99
100	11	100
101	11	101
102	11	102
103	11	103
104	11	104
105	11	105
106	11	106
107	11	107
108	11	108
109	11	109
110	11	110
111	11	111
112	11	112
113	11	113
114	11	114
115	11	115
116	11	116
117	11	117
118	11	118
119	11	119
120	11	120
121	11	121
122	11	122
123	11	123
124	11	124
125	11	125
126	11	126
127	11	127
128	11	128
129	11	129
130	11	130
131	11	131
132	11	132
133	11	133
134	11	134
135	11	135
136	11	136
137	11	137
138	11	138
139	11	139
140	11	140
141	11	141
142	11	142
143	11	143
144	11	144
145	11	145
146	11	146
147	11	147
148	11	148
149	11	149
150	11	150
151	11	151
152	11	152
153	11	153
154	11	154
155	11	155
156	11	156
157	11	157
158	11	158
159	11	159
160	11	160
161	11	161
162	11	162
163	11	163
164	11	164
165	11	165
166	11	166
167	11	167
168	11	168
169	11	169
170	11	170
171	11	171
172	11	172
173	11	173
174	11	174
175	11	175
176	11	176
177	11	177
178	11	178
179	11	179
180	11	180
181	11	181
182	11	182
183	11	183
184	11	184
185	11	185
186	11	186
187	11	187
188	11	188
189	11	189
190	11	190
191	11	191
192	11	192
193	11	193
194	11	194
195	11	195
196	11	196
197	11	197
198	11	198
199	11	199
200	11	200
201	11	201
202	11	202
203	11	203
204	11	204
205	11	205
206	11	206
207	11	207
208	11	208
209	11	209
210	11	210
211	11	211
212	11	212
213	11	213
214	11	214
215	11	215
216	11	216
217	11	217
218	11	218
219	11	219
220	11	220
221	11	221
222	11	222
223	11	223
224	11	224
225	11	225
226	11	226
227	11	227
228	11	228
229	11	229
230	11	230
231	11	231
232	11	232
233	11	233
234	11	234
235	11	235
236	11	236
237	11	237
238	11	238
239	11	239
240	11	240
241	11	241
242	11	242
243	11	243
244	11	244
245	11	245
246	11	246
247	11	247
248	11	248
249	11	249
250	11	250
251	11	251
252	11	252
253	11	253
254	11	254
255	11	255
256	11	256
257	11	257
258	11	258
259	11	259
260	11	260
261	11	261
262	11	262
263	11	263
264	11	264
265	11	265
266	11	266
267	11	267
268	11	268
269	11	269
270	11	270
271	11	271
272	11	272
273	11	273
274	11	274
275	11	275
276	11	276
277	11	277
278	11	278
279	11	279
280	11	280
281	11	281
282	11	282
283	11	283
284	11	284
285	11	285
286	11	286
287	11	287
288	11	288
289	11	289
290	11	290
291	11	291
292	11	292
293	11	293
294	11	294
295	11	295
296	11	296
297	11	297
298	11	298
299	11	299
300	11	300
301	11	301
302	11	302
303	11	303
304	11	304
305	11	305
306	11	306
307	11	307
308	11	308
309	11	309
310	11	310
311	11	311
312	11	312
313	11	313
314	11	314
315	11	315
316	11	316
317	11	317
318	11	318
319	11	319
320	11	320
321	11	321
322	11	322
323	11	323
324	11	324
325	11	325
326	11	326
327	11	327
328	11	328
329	11	329
330	11	330
331	11	331
332	11	332
333	11	333
334	11	334
335	11	335
336	11	336
337	11	337
338	11	338
339	11	339
340	11	340
341	11	341
342	11	342
343	11	343
344	11	344
345	11	345
346	11	346
347	11	347
348	11	348
349	11	349
350	11	350
351	11	351
352	11	352
353	11	353
354	11	354
355	11	355
356	11	356
357	11	357
358	11	358
359	11	359
360	11	360
361	11	361
362	11	362
363	11	363
364	11	364
365	11	365
366	11	366
367	11	367
368	11	368
369	11	369
370	11	370
371	11	371
372	11	372
373	11	373
374	11	374
375	11	375
376	11	376
377	11	377
378	11	378
379	11	379
\.


--
-- Data for Name: accounts_userdocument; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.accounts_userdocument (id, user_document_type, user_document_number, user_document_photo, user_id) FROM stdin;
\.


--
-- Data for Name: addresses_address; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.addresses_address (id, nick_name, address_line1, address_contact_name, address_contact_number, pincode, address_type, latitude, longitude, created_at, modified_at, status, city_id, shop_name_id, state_id) FROM stdin;
1	\N	Greater Noida	Greater Noida			shipping	0	0	2019-01-08 11:45:32.206408+00	2019-01-08 11:45:32.206426+00	t	1	1	1
2	\N	GN-BIlling	GN-Billing			billing	0	0	2019-01-08 12:09:40.739756+00	2019-01-08 12:09:40.739783+00	t	1	1	1
4	golu	story short 6	serinfg	8567075678	112233	shipping	0	0	2019-01-08 12:38:17.312954+00	2019-01-08 12:38:17.312976+00	f	1	3	1
5	Mayank sir	mayank ke ghar	mayank ustaad	9988536264	140114	billing	0	0	2019-01-08 12:49:02.330746+00	2019-01-08 12:49:02.33077+00	f	1	3	1
6	Arzoo Ka Address	Near DLF Mall Of India	Mayank Prajapat	9899746673	122542	shipping	0	0	2019-01-09 06:23:21.824542+00	2019-01-09 06:23:21.824566+00	f	1	4	1
7	Billing Vala Ghar	Near Baraktulla Khan Cricket Stadium	Ashish Vyas	9899653325	342003	billing	0	0	2019-01-09 06:42:49.312209+00	2019-01-09 06:42:49.312237+00	f	1	4	1
8	pal pal	931P	pallavi	7763886418	124578	shipping	0	0	2019-01-09 07:12:27.475991+00	2019-01-09 07:12:27.476015+00	f	1	5	1
9	khud ka ghar	house number zyz	nikita	9699899985	659965	shipping	0	0	2019-01-09 08:02:02.600418+00	2019-01-09 08:02:02.600449+00	f	3	6	3
10	billing address	arbit adress	nikita ka bhai	9899856632	659986	billing	0	0	2019-01-09 08:05:20.889667+00	2019-01-09 08:05:20.889696+00	f	3	6	3
11	\N	18C, Knowledge Park 3, Greator Noida,	Anil Kumar	9582288240	301206	billing	0	0	2019-01-09 10:59:36.55743+00	2019-01-09 10:59:36.55746+00	t	5	7	1
12	\N	18C, Knowledge Park 3, Greator Noida,	Anil Kumar	9582288240	301206	shipping	0	0	2019-01-09 10:59:36.559085+00	2019-01-09 10:59:36.559126+00	t	5	7	1
13	delhi	Delhi	hdhdb	7042545165	110042	shipping	0	0	2019-01-09 11:55:57.066047+00	2019-01-09 11:55:57.066074+00	f	3	8	3
14	delhi	delhi	bans	7849497619	100448	billing	0	0	2019-01-09 13:15:22.739158+00	2019-01-09 13:15:22.739187+00	f	3	8	3
\.


--
-- Data for Name: addresses_area; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.addresses_area (id, area_name, created_at, modified_at, status, city_id) FROM stdin;
\.


--
-- Data for Name: addresses_city; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.addresses_city (id, city_name, created_at, modified_at, status, country_id, state_id) FROM stdin;
1	Noida	2019-01-08 11:43:51.942016+00	2019-01-08 11:43:51.942045+00	t	1	1
2	Sonipat	2019-01-09 07:12:48.355808+00	2019-01-09 07:12:48.355835+00	t	1	2
3	Karol Bagh	2019-01-09 07:13:02.452982+00	2019-01-09 07:13:02.45301+00	t	1	3
4	Gurgaon	2019-01-09 07:13:12.264945+00	2019-01-09 07:13:12.264973+00	t	1	2
5	Greater Noida	2019-01-09 07:13:28.3274+00	2019-01-09 07:13:28.327433+00	t	1	1
\.


--
-- Data for Name: addresses_country; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.addresses_country (id, country_name, created_at, modified_at, status) FROM stdin;
1	India	2019-01-08 11:43:15.449937+00	2019-01-08 11:43:15.449961+00	t
\.


--
-- Data for Name: addresses_invoicecitymapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.addresses_invoicecitymapping (id, city_code, city_id) FROM stdin;
\.


--
-- Data for Name: addresses_state; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.addresses_state (id, state_name, created_at, modified_at, status, country_id) FROM stdin;
1	Uttar Pradesh	2019-01-08 11:43:34.689444+00	2019-01-08 11:43:34.689469+00	t	1
2	Haryana	2019-01-09 07:12:14.608981+00	2019-01-09 07:12:14.609008+00	t	1
3	New Delhi	2019-01-09 07:12:26.527925+00	2019-01-09 07:12:26.527949+00	t	1
\.


--
-- Data for Name: allauth_socialaccount; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.allauth_socialaccount (id, provider, uid, last_login, date_joined, extra_data, user_id) FROM stdin;
\.


--
-- Data for Name: allauth_socialapp; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.allauth_socialapp (id, provider, name, client_id, secret, key) FROM stdin;
\.


--
-- Data for Name: allauth_socialapp_sites; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.allauth_socialapp_sites (id, socialapp_id, site_id) FROM stdin;
\.


--
-- Data for Name: allauth_socialtoken; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.allauth_socialtoken (id, token, token_secret, expires_at, account_id, app_id) FROM stdin;
\.


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add group	2	add_group
6	Can change group	2	change_group
7	Can delete group	2	delete_group
8	Can view group	2	view_group
9	Can add permission	3	add_permission
10	Can change permission	3	change_permission
11	Can delete permission	3	delete_permission
12	Can view permission	3	view_permission
13	Can add content type	4	add_contenttype
14	Can change content type	4	change_contenttype
15	Can delete content type	4	delete_contenttype
16	Can view content type	4	view_contenttype
17	Can add session	5	add_session
18	Can change session	5	change_session
19	Can delete session	5	delete_session
20	Can view session	5	view_session
21	Can add Token	6	add_token
22	Can change Token	6	change_token
23	Can delete Token	6	delete_token
24	Can view Token	6	view_token
25	Can add site	7	add_site
26	Can change site	7	change_site
27	Can delete site	7	delete_site
28	Can view site	7	view_site
29	Can add social application token	8	add_socialtoken
30	Can change social application token	8	change_socialtoken
31	Can delete social application token	8	delete_socialtoken
32	Can view social application token	8	view_socialtoken
33	Can add social application	9	add_socialapp
34	Can change social application	9	change_socialapp
35	Can delete social application	9	delete_socialapp
36	Can view social application	9	view_socialapp
37	Can add social account	10	add_socialaccount
38	Can change social account	10	change_socialaccount
39	Can delete social account	10	delete_socialaccount
40	Can view social account	10	view_socialaccount
41	Can add email address	11	add_emailaddress
42	Can change email address	11	change_emailaddress
43	Can delete email address	11	delete_emailaddress
44	Can view email address	11	view_emailaddress
45	Can add email confirmation	12	add_emailconfirmation
46	Can change email confirmation	12	change_emailconfirmation
47	Can delete email confirmation	12	delete_emailconfirmation
48	Can view email confirmation	12	view_emailconfirmation
49	Can add user document	13	add_userdocument
50	Can change user document	13	change_userdocument
51	Can delete user document	13	delete_userdocument
52	Can view user document	13	view_userdocument
53	Can add user	14	add_user
54	Can change user	14	change_user
55	Can delete user	14	delete_user
56	Can view user	14	view_user
57	Can add Phone OTP	15	add_phoneotp
58	Can change Phone OTP	15	change_phoneotp
59	Can delete Phone OTP	15	delete_phoneotp
60	Can view Phone OTP	15	view_phoneotp
61	Can add category posation	16	add_categoryposation
62	Can change category posation	16	change_categoryposation
63	Can delete category posation	16	delete_categoryposation
64	Can view category posation	16	view_categoryposation
65	Can add category data	17	add_categorydata
66	Can change category data	17	change_categorydata
67	Can delete category data	17	delete_categorydata
68	Can view category data	17	view_categorydata
69	Can add category	18	add_category
70	Can change category	18	change_category
71	Can delete category	18	delete_category
72	Can view category	18	view_category
73	Can add invoice city mapping	19	add_invoicecitymapping
74	Can change invoice city mapping	19	change_invoicecitymapping
75	Can delete invoice city mapping	19	delete_invoicecitymapping
76	Can view invoice city mapping	19	view_invoicecitymapping
77	Can add city	20	add_city
78	Can change city	20	change_city
79	Can delete city	20	delete_city
80	Can view city	20	view_city
81	Can add state	21	add_state
82	Can change state	21	change_state
83	Can delete state	21	delete_state
84	Can view state	21	view_state
85	Can add country	22	add_country
86	Can change country	22	change_country
87	Can delete country	22	delete_country
88	Can view country	22	view_country
89	Can add address	23	add_address
90	Can change address	23	change_address
91	Can delete address	23	delete_address
92	Can view address	23	view_address
93	Can add area	24	add_area
94	Can change area	24	change_area
95	Can delete area	24	delete_area
96	Can view area	24	view_area
97	Can add product category history	25	add_productcategoryhistory
98	Can change product category history	25	change_productcategoryhistory
99	Can delete product category history	25	delete_productcategoryhistory
100	Can view product category history	25	view_productcategoryhistory
101	Can add fragrance	26	add_fragrance
102	Can change fragrance	26	change_fragrance
103	Can delete fragrance	26	delete_fragrance
104	Can view fragrance	26	view_fragrance
105	Can add product vendor mapping	27	add_productvendormapping
106	Can change product vendor mapping	27	change_productvendormapping
107	Can delete product vendor mapping	27	delete_productvendormapping
108	Can view product vendor mapping	27	view_productvendormapping
109	Can add product image	28	add_productimage
110	Can change product image	28	change_productimage
111	Can delete product image	28	delete_productimage
112	Can view product image	28	view_productimage
113	Can add product price	29	add_productprice
114	Can change product price	29	change_productprice
115	Can delete product price	29	delete_productprice
116	Can view product price	29	view_productprice
117	Can add weight	30	add_weight
118	Can change weight	30	change_weight
119	Can delete weight	30	delete_weight
120	Can view weight	30	view_weight
121	Can add tax	31	add_tax
122	Can change tax	31	change_tax
123	Can delete tax	31	delete_tax
124	Can view tax	31	view_tax
125	Can add product option	32	add_productoption
126	Can change product option	32	change_productoption
127	Can delete product option	32	delete_productoption
128	Can view product option	32	view_productoption
129	Can add product sku generator	33	add_productskugenerator
130	Can change product sku generator	33	change_productskugenerator
131	Can delete product sku generator	33	delete_productskugenerator
132	Can view product sku generator	33	view_productskugenerator
133	Can add product history	34	add_producthistory
134	Can change product history	34	change_producthistory
135	Can delete product history	34	delete_producthistory
136	Can view product history	34	view_producthistory
137	Can add product csv	35	add_productcsv
138	Can change product csv	35	change_productcsv
139	Can delete product csv	35	delete_productcsv
140	Can view product csv	35	view_productcsv
141	Can add product	36	add_product
142	Can change product	36	change_product
143	Can delete product	36	delete_product
144	Can view product	36	view_product
145	Can add color	37	add_color
146	Can change color	37	change_color
147	Can delete color	37	delete_color
148	Can view color	37	view_color
149	Can add package size	38	add_packagesize
150	Can change package size	38	change_packagesize
151	Can delete package size	38	delete_packagesize
152	Can view package size	38	view_packagesize
153	Can add flavor	39	add_flavor
154	Can change flavor	39	change_flavor
155	Can delete flavor	39	delete_flavor
156	Can view flavor	39	view_flavor
157	Can add product category	40	add_productcategory
158	Can change product category	40	change_productcategory
159	Can delete product category	40	delete_productcategory
160	Can view product category	40	view_productcategory
161	Can add product tax mapping	41	add_producttaxmapping
162	Can change product tax mapping	41	change_producttaxmapping
163	Can delete product tax mapping	41	delete_producttaxmapping
164	Can view product tax mapping	41	view_producttaxmapping
165	Can add size	42	add_size
166	Can change size	42	change_size
167	Can delete size	42	delete_size
168	Can view size	42	view_size
169	Can add product price csv	43	add_productpricecsv
170	Can change product price csv	43	change_productpricecsv
171	Can delete product price csv	43	delete_productpricecsv
172	Can view product price csv	43	view_productpricecsv
173	Can add shop	44	add_shop
174	Can change shop	44	change_shop
175	Can delete shop	44	delete_shop
176	Can view shop	44	view_shop
177	Can add shop document	45	add_shopdocument
178	Can change shop document	45	change_shopdocument
179	Can delete shop document	45	delete_shopdocument
180	Can view shop document	45	view_shopdocument
181	Can add parent retailer mapping	46	add_parentretailermapping
182	Can change parent retailer mapping	46	change_parentretailermapping
183	Can delete parent retailer mapping	46	delete_parentretailermapping
184	Can view parent retailer mapping	46	view_parentretailermapping
185	Can add shop type	47	add_shoptype
186	Can change shop type	47	change_shoptype
187	Can delete shop type	47	delete_shoptype
188	Can view shop type	47	view_shoptype
189	Can add shop photo	48	add_shopphoto
190	Can change shop photo	48	change_shopphoto
191	Can delete shop photo	48	delete_shopphoto
192	Can view shop photo	48	view_shopphoto
193	Can add retailer type	49	add_retailertype
194	Can change retailer type	49	change_retailertype
195	Can delete retailer type	49	delete_retailertype
196	Can view retailer type	49	view_retailertype
197	Can add brand position	50	add_brandposition
198	Can change brand position	50	change_brandposition
199	Can delete brand position	50	delete_brandposition
200	Can view brand position	50	view_brandposition
201	Can add brand	51	add_brand
202	Can change brand	51	change_brand
203	Can delete brand	51	delete_brand
204	Can view brand	51	view_brand
205	Can add vendor	52	add_vendor
206	Can change vendor	52	change_vendor
207	Can delete vendor	52	delete_vendor
208	Can view vendor	52	view_vendor
209	Can add brand data	53	add_branddata
210	Can change brand data	53	change_branddata
211	Can delete brand data	53	delete_branddata
212	Can view brand data	53	view_branddata
213	Can add page	54	add_page
214	Can change page	54	change_page
215	Can delete page	54	delete_page
216	Can view page	54	view_page
217	Can add banner position	55	add_bannerposition
218	Can change banner position	55	change_bannerposition
219	Can delete banner position	55	delete_bannerposition
220	Can view banner position	55	view_bannerposition
221	Can add banner	56	add_banner
222	Can change banner	56	change_banner
223	Can delete banner	56	delete_banner
224	Can view banner	56	view_banner
225	Can add banner slot	57	add_bannerslot
226	Can change banner slot	57	change_bannerslot
227	Can delete banner slot	57	delete_bannerslot
228	Can view banner slot	57	view_bannerslot
229	Can add banner data	58	add_bannerdata
230	Can change banner data	58	change_bannerdata
231	Can delete banner data	58	delete_bannerdata
232	Can view banner data	58	view_bannerdata
233	Can add Purchase Order Item List	59	add_orderitem
234	Can change Purchase Order Item List	59	change_orderitem
235	Can delete Purchase Order Item List	59	delete_orderitem
236	Can view Purchase Order Item List	59	view_orderitem
237	Can add grn order product mapping	60	add_grnorderproductmapping
238	Can change grn order product mapping	60	change_grnorderproductmapping
239	Can delete grn order product mapping	60	delete_grnorderproductmapping
240	Can view grn order product mapping	60	view_grnorderproductmapping
241	Can add po_ message	61	add_po_message
242	Can change po_ message	61	change_po_message
243	Can delete po_ message	61	delete_po_message
244	Can view po_ message	61	view_po_message
245	Can add order history	62	add_orderhistory
246	Can change order history	62	change_orderhistory
247	Can delete order history	62	delete_orderhistory
248	Can view order history	62	view_orderhistory
249	Can add pick list items	63	add_picklistitems
250	Can change pick list items	63	change_picklistitems
251	Can delete pick list items	63	delete_picklistitems
252	Can view pick list items	63	view_picklistitems
253	Can add ordered product reserved	64	add_orderedproductreserved
254	Can change ordered product reserved	64	change_orderedproductreserved
255	Can delete ordered product reserved	64	delete_orderedproductreserved
256	Can view ordered product reserved	64	view_orderedproductreserved
257	Can add PO Generation	65	add_cart
258	Can change PO Generation	65	change_cart
259	Can delete PO Generation	65	delete_cart
260	Can view PO Generation	65	view_cart
261	Can approve and dis-approve	65	can_approve_and_disapprove
262	Can add Select Product	66	add_cartproductmapping
263	Can change Select Product	66	change_cartproductmapping
264	Can delete Select Product	66	delete_cartproductmapping
265	Can view Select Product	66	view_cartproductmapping
266	Can add grn order product history	67	add_grnorderproducthistory
267	Can change grn order product history	67	change_grnorderproducthistory
268	Can delete grn order product history	67	delete_grnorderproducthistory
269	Can view grn order product history	67	view_grnorderproducthistory
270	Can add order	68	add_order
271	Can change order	68	change_order
272	Can delete order	68	delete_order
273	Can view order	68	view_order
274	Can add grn order	69	add_grnorder
275	Can change grn order	69	change_grnorder
276	Can delete grn order	69	delete_grnorder
277	Can view grn order	69	view_grnorder
278	Can add pick list	70	add_picklist
279	Can change pick list	70	change_picklist
280	Can delete pick list	70	delete_picklist
281	Can view pick list	70	view_picklist
282	Can add brand note	71	add_brandnote
283	Can change brand note	71	change_brandnote
284	Can delete brand note	71	delete_brandnote
285	Can view brand note	71	view_brandnote
286	Can add ordered product	72	add_orderedproduct
287	Can change ordered product	72	change_orderedproduct
288	Can delete ordered product	72	delete_orderedproduct
289	Can view ordered product	72	view_orderedproduct
290	Can add ordered product reserved	73	add_orderedproductreserved
291	Can change ordered product reserved	73	change_orderedproductreserved
292	Can delete ordered product reserved	73	delete_orderedproductreserved
293	Can view ordered product reserved	73	view_orderedproductreserved
294	Can add sp note	74	add_spnote
295	Can change sp note	74	change_spnote
296	Can delete sp note	74	delete_spnote
297	Can view sp note	74	view_spnote
298	Can add Select Product	75	add_cartproductmapping
299	Can change Select Product	75	change_cartproductmapping
300	Can delete Select Product	75	delete_cartproductmapping
301	Can view Select Product	75	view_cartproductmapping
302	Can add PO Generation	76	add_cart
303	Can change PO Generation	76	change_cart
304	Can delete PO Generation	76	delete_cart
305	Can view PO Generation	76	view_cart
306	Can add order	77	add_order
307	Can change order	77	change_order
308	Can delete order	77	delete_order
309	Can view order	77	view_order
310	Can add ordered product mapping	78	add_orderedproductmapping
311	Can change ordered product mapping	78	change_orderedproductmapping
312	Can delete ordered product mapping	78	delete_orderedproductmapping
313	Can view ordered product mapping	78	view_orderedproductmapping
314	Can Delivery From GF	78	delivery_from_gf
315	Can Warehouse Shipment	78	warehouse_shipment
316	Can add ordered product mapping	79	add_orderedproductmapping
317	Can change ordered product mapping	79	change_orderedproductmapping
318	Can delete ordered product mapping	79	delete_orderedproductmapping
319	Can view ordered product mapping	79	view_orderedproductmapping
320	Can add payment	80	add_payment
321	Can change payment	80	change_payment
322	Can delete payment	80	delete_payment
323	Can view payment	80	view_payment
324	Can add customer care	81	add_customercare
325	Can change customer care	81	change_customercare
326	Can delete customer care	81	delete_customercare
327	Can view customer care	81	view_customercare
328	Can add note	82	add_note
329	Can change note	82	change_note
330	Can delete note	82	delete_note
331	Can view note	82	view_note
332	Can add order	83	add_order
333	Can change order	83	change_order
334	Can delete order	83	delete_order
335	Can view order	83	view_order
336	Can add cart	84	add_cart
337	Can change cart	84	change_cart
338	Can delete cart	84	delete_cart
339	Can view cart	84	view_cart
340	Can add cart product mapping	85	add_cartproductmapping
341	Can change cart product mapping	85	change_cartproductmapping
342	Can delete cart product mapping	85	delete_cartproductmapping
343	Can view cart product mapping	85	view_cartproductmapping
344	Can add ordered product	86	add_orderedproduct
345	Can change ordered product	86	change_orderedproduct
346	Can delete ordered product	86	delete_orderedproduct
347	Can view ordered product	86	view_orderedproduct
348	Can add cart	87	add_cart
349	Can change cart	87	change_cart
350	Can delete cart	87	delete_cart
351	Can view cart	87	view_cart
352	Can add customer care	88	add_customercare
353	Can change customer care	88	change_customercare
354	Can delete customer care	88	delete_customercare
355	Can view customer care	88	view_customercare
356	Can add ordered product mapping	89	add_orderedproductmapping
357	Can change ordered product mapping	89	change_orderedproductmapping
358	Can delete ordered product mapping	89	delete_orderedproductmapping
359	Can view ordered product mapping	89	view_orderedproductmapping
360	Can add payment	90	add_payment
361	Can change payment	90	change_payment
362	Can delete payment	90	delete_payment
363	Can view payment	90	view_payment
364	Can add note	91	add_note
365	Can change note	91	change_note
366	Can delete note	91	delete_note
367	Can view note	91	view_note
368	Can add ordered product	92	add_orderedproduct
369	Can change ordered product	92	change_orderedproduct
370	Can delete ordered product	92	delete_orderedproduct
371	Can view ordered product	92	view_orderedproduct
372	Can add order	93	add_order
373	Can change order	93	change_order
374	Can delete order	93	delete_order
375	Can view order	93	view_order
376	Can add cart product mapping	94	add_cartproductmapping
377	Can change cart product mapping	94	change_cartproductmapping
378	Can delete cart product mapping	94	delete_cartproductmapping
379	Can view cart product mapping	94	view_cartproductmapping
\.


--
-- Data for Name: authtoken_token; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.authtoken_token (key, created, user_id) FROM stdin;
fdd4df52e96b629c406e8dba0545ce3585179de2	2019-01-07 12:28:54.225166+00	1
99f47cf880adb5658bcbd696a8d3603217417f28	2019-01-07 16:36:59.664525+00	2
b9d7377d1e42eecbfb93e9c81b41bfb99ec45a89	2019-01-08 06:40:25.242445+00	4
46731a99947a7056073ab35fe7494ee602b1e156	2019-01-08 12:36:52.583246+00	6
9a838c6afdc9b95e399e380e97061f0f2d6706d6	2019-01-08 12:49:06.401789+00	7
4161bc26c05a98eb881fd93512d82743f309d490	2019-01-09 06:21:00.442883+00	8
4bb1b025fb2c1df90d7586f7d543de2914176822	2019-01-09 07:09:36.952018+00	9
f39515c43322f59cd3d11ded33a94f2b5cfabb25	2019-01-09 08:00:52.37652+00	10
cc42a890ba4be93f849d9e5a71104dffafd45ff0	2019-01-09 09:46:30.73304+00	11
7dc13ae33b36aa32573e43d436636cffdfae8e80	2019-01-09 10:53:34.055568+00	12
7d0e9c4e2af7a72690647a18152cecec4452c29e	2019-01-09 11:55:10.67026+00	13
\.


--
-- Data for Name: banner_banner; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.banner_banner (id, name, image, created_at, updated_at, banner_start_date, banner_end_date, status, alt_text, text_below_image) FROM stdin;
2	Goldee	banner_I6.png	2019-01-08 12:17:50.053701+00	2019-01-09 07:16:27.727164+00	2019-01-02 00:30:00+00	2019-04-11 00:30:00+00	t	GOL	\N
1	Marico	banner_78.png	2019-01-08 12:16:42.36639+00	2019-01-09 07:17:01.419937+00	2019-01-02 00:30:00+00	2019-04-12 12:30:00+00	t	MAR	\N
3	GramFactory	banner_56.png	2019-01-09 07:18:03.214049+00	2019-01-09 07:18:03.214083+00	2019-01-07 07:17:52+00	2019-05-07 00:30:00+00	t	GramFactory	\N
4	lyzol	banner_60.png	2019-01-09 07:20:03.665885+00	2019-01-09 07:20:03.665927+00	2019-01-01 00:30:00+00	2019-05-09 00:30:00+00	t	lyzol	\N
5	snacks	banner_24.png	2019-01-09 07:22:16.246595+00	2019-01-09 07:22:39.635054+00	2019-01-07 06:30:00+00	2019-04-20 06:30:00+00	t	snacks	\N
6	cream	banner_37.png	2019-01-09 07:23:40.407548+00	2019-01-09 07:23:40.407581+00	2019-01-08 00:30:00+00	2019-04-05 06:30:00+00	t	cream	\N
\.


--
-- Data for Name: banner_bannerdata; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.banner_bannerdata (id, banner_data_order, banner_data_id, slot_id) FROM stdin;
1	1	1	1
2	2	2	1
3	3	3	1
4	4	4	1
5	5	5	1
6	6	6	1
\.


--
-- Data for Name: banner_bannerposition; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.banner_bannerposition (id, banner_position_order, bannerslot_id, page_id) FROM stdin;
1	1	1	1
\.


--
-- Data for Name: banner_bannerslot; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.banner_bannerslot (id, name, page_id) FROM stdin;
1	homepage-slot1	1
\.


--
-- Data for Name: banner_page; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.banner_page (id, name) FROM stdin;
1	HomePage
\.


--
-- Data for Name: brand_brand; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.brand_brand (id, brand_name, brand_slug, brand_logo, brand_description, brand_code, created_at, updated_at, active_status, brand_parent_id) FROM stdin;
1	Dabur	dabur	Dabur.jpg		DBR	2019-01-08 07:24:36.97269+00	2019-01-08 07:24:36.972725+00	1	\N
2	Fena	fena	Fena.jpg		FNA	2019-01-08 07:25:00.359638+00	2019-01-08 07:25:00.359672+00	1	\N
3	Ghadi	ghadi	Ghadi.jpg		GHD	2019-01-08 07:25:34.606556+00	2019-01-08 07:25:34.60659+00	1	\N
7	Reckitt Benckiser	reckitt-benckiser	Reckitt_Benckiser.jpg		RBI	2019-01-08 07:27:20.964906+00	2019-01-08 07:27:20.964939+00	1	\N
8	Harpic	harpic	Harpic.jpg		HRP	2019-01-08 07:28:42.492178+00	2019-01-08 07:28:42.49221+00	1	7
9	Dabur Amla	dabur-amla	Dabur_Amla.jpg		DAM	2019-01-08 11:17:40.553093+00	2019-01-08 11:17:40.553126+00	1	1
10	Dabur Red	dabur-red	Dabur_Red.jpg		DRE	2019-01-08 11:18:03.794167+00	2019-01-08 11:18:03.794198+00	1	1
11	Meswak	meswak	Meswak.jpg		DME	2019-01-08 11:18:25.668714+00	2019-01-08 11:18:25.668748+00	1	1
13	NIP	nip	NIP.jpg		FNI	2019-01-08 11:19:17.889454+00	2019-01-08 11:19:17.889488+00	1	2
14	Godrej Expert	godrej-expert	Godrej_Expert.jpg		GEX	2019-01-08 11:19:38.898729+00	2019-01-08 11:19:38.898761+00	1	4
15	Godrej No. 1	godrej-no-1	Godrej_No._1.jpg		GNO	2019-01-08 11:20:06.123897+00	2019-01-08 11:20:06.123929+00	1	4
16	Godrej Nupur	godrej-nupur	Godrej_Nupur.jpg		GNU	2019-01-08 11:20:29.761+00	2019-01-08 11:20:29.761032+00	1	4
17	Good knight	good-knight	Good_knight.jpg		GGN	2019-01-08 11:21:22.995749+00	2019-01-08 11:21:22.99578+00	1	4
18	DOVE	dove	DOVE.jpg		DOV	2019-01-08 11:22:09.281181+00	2019-01-08 11:22:09.281214+00	1	5
19	FAIR & LOVELY	fair-lovely	FAIR__LOVELY.jpg		FAL	2019-01-08 11:23:22.207047+00	2019-01-08 11:23:22.207078+00	1	5
20	Lifebuoy	lifebuoy	Lifebuoy.jpg		LIF	2019-01-08 11:23:51.237033+00	2019-01-08 11:23:51.237061+00	1	5
21	LUX	lux	LUX_PINK.jpg		LUX	2019-01-08 11:24:57.612739+00	2019-01-08 11:24:57.612783+00	1	5
22	PONDS	ponds	PONDS.jpg		PND	2019-01-08 11:26:25.041271+00	2019-01-08 11:26:25.041302+00	1	5
23	RIN	rin	RIN.jpg		RIN	2019-01-08 11:26:51.766736+00	2019-01-08 11:26:51.76677+00	1	5
24	TRESEMME	tresemme	TRESEMME.jpg		TRE	2019-01-08 11:28:21.407847+00	2019-01-08 11:28:21.40788+00	1	5
25	VASELINE	vaseline	VASELINE.jpg		VAS	2019-01-08 11:28:38.052461+00	2019-01-08 11:28:38.052494+00	1	5
26	Wheel	wheel	Wheel.jpg		WHE	2019-01-08 11:28:56.126602+00	2019-01-08 11:28:56.126634+00	1	5
29	Cherry Blossom	cherry-blossom	Cherry_Blossom.jpg		CHR	2019-01-08 11:30:39.095503+00	2019-01-08 11:30:39.095535+00	1	7
30	Dettol	dettol	Dettol.jpg		DET	2019-01-08 11:30:57.081747+00	2019-01-08 11:30:57.081777+00	1	7
32	Moov	moov	Moov.jpg		MOV	2019-01-08 11:31:55.024731+00	2019-01-08 11:31:55.024763+00	1	7
33	Veet	veet	Veet.jpg		VET	2019-01-08 11:33:14.615875+00	2019-01-08 11:33:14.615906+00	1	7
34	Nestle	nestle	Nestle-Logo.jpg		NES	2019-01-08 13:17:18.300434+00	2019-01-08 13:17:18.30047+00	1	\N
35	Maggi	maggi	Maggi_logo.jpg		MAG	2019-01-08 13:17:52.583024+00	2019-01-08 13:17:52.583056+00	1	34
36	Everyday	everyday	everyday_logo.png		EVD	2019-01-08 13:18:40.31008+00	2019-01-08 13:18:40.310113+00	1	34
37	Cerelac	cerelac	cerelac_image.jpg		CER	2019-01-08 13:19:09.287008+00	2019-01-08 13:19:09.287041+00	1	34
38	Lactogen	lactogen	lactogen_logo.jpg		LAC	2019-01-08 13:19:44.248362+00	2019-01-08 13:19:44.248395+00	1	34
39	ITC	itc	ITC_image.jpg		ITC	2019-01-08 13:20:07.36+00	2019-01-08 13:20:07.360035+00	1	\N
41	Bingo	bingo	bingo-logo-big.jpg		BNG	2019-01-08 13:21:30.795822+00	2019-01-08 13:21:30.795855+00	1	39
42	Yippee	yippee	yippee_logo.jpg		YIP	2019-01-08 13:21:57.720985+00	2019-01-08 13:21:57.721016+00	1	39
43	Kellogg's	kelloggs	Kelloggs_logo.jpg		KEL	2019-01-08 13:22:54.934689+00	2019-01-08 13:22:54.934723+00	1	\N
44	Cornflakes	cornflakes	kelloggs_corn_flakes_logo.jpg		CNF	2019-01-08 13:23:25.708729+00	2019-01-08 13:23:25.708761+00	1	43
45	Chocos	chocos	chocos_image_logo.jpg		CHO	2019-01-08 13:24:03.823484+00	2019-01-08 13:24:03.823516+00	1	43
46	Fritolay	fritolay	fritolay_image_logo.jpg		FIL	2019-01-08 13:24:41.32426+00	2019-01-08 13:24:41.324293+00	1	\N
47	Lay's	lays	Lays_image_logo.jpg		LAY	2019-01-08 13:25:17.695152+00	2019-01-08 13:25:17.695185+00	1	46
48	Doritos	doritos	doritos_logo_image.jpg		DOR	2019-01-08 13:25:50.514775+00	2019-01-08 13:25:50.514807+00	1	46
49	Quaker	quaker	quaker_image_logo.jpg		QKR	2019-01-08 13:26:29.880813+00	2019-01-08 13:26:29.880846+00	1	46
50	Haldiram	haldiram	Haldiram_logo.jpg		HAL	2019-01-08 13:27:11.983376+00	2019-01-08 13:27:11.983412+00	1	\N
51	Haldiram Snacks	haldiram-snacks	Haldiram_logo.jpg		HAS	2019-01-08 13:28:24.218979+00	2019-01-08 13:28:24.219013+00	1	50
55	ITC Limited	itc-limited	ITC_Limited.jpg		ITC	2019-01-08 13:42:41.499619+00	2019-01-08 13:42:41.499655+00	1	\N
56	P&G	pg	PG.jpg		PNG	2019-01-08 13:42:59.388029+00	2019-01-08 13:42:59.388064+00	1	\N
63	Sunsilk	sunsilk	Sunsilk.jpg		SUN	2019-01-08 13:48:01.695245+00	2019-01-08 13:48:01.695284+00	1	5
73	Dabur Almond	dabur-almond	Dabur_Almond.jpg		DAL	2019-01-08 13:55:27.273429+00	2019-01-09 10:34:51.777301+00	1	1
78	Gillete	gillete	Gillete.jpg		GIL	2019-01-08 14:02:35.263651+00	2019-01-08 14:02:35.263682+00	1	56
79	Pampers	pampers	Pampers.jpg		PAM	2019-01-08 14:02:58.718135+00	2019-01-08 14:02:58.718168+00	1	56
80	Robin	robin	Robin.jpg		ROB	2019-01-08 14:03:50.195505+00	2019-01-08 14:03:50.195535+00	1	7
81	Tide	tide	Tide.jpg		TID	2019-01-08 14:04:13.349361+00	2019-01-08 14:04:13.349393+00	1	56
82	Vicks	vicks	Vicks.jpg		VIC	2019-01-08 14:04:39.18906+00	2019-01-08 14:04:39.189092+00	1	56
84	Saffola Oats	saffola-oats	saffola-oats-logo.jpg		SOA	2019-01-09 04:29:52.169236+00	2019-01-09 04:29:52.169269+00	1	6
77	CLINIC PLUS	clinic-plus	clinicplus.jpg		CLI	2019-01-08 13:57:29.340569+00	2019-01-09 10:33:27.051663+00	1	5
76	CLOSE UP	close	closeup.jpg		CLP	2019-01-08 13:57:05.322244+00	2019-01-09 10:33:52.832196+00	1	5
75	Colgate_Brand	colgate_brand	Colgate_Brand.jpg		CLB	2019-01-08 13:56:38.657272+00	2019-01-09 10:34:12.038481+00	1	57
57	Colgate	colgate	Colgate_Brand.jpg		COL	2019-01-08 13:43:19.261459+00	2019-01-09 10:34:22.557399+00	1	\N
74	Colin	colin	colin.jpg		CLN	2019-01-08 13:55:46.312068+00	2019-01-09 10:34:37.582452+00	1	7
72	Engage	engage	Engage.jpg		ENG	2019-01-08 13:55:06.464037+00	2019-01-09 10:35:06.493229+00	1	39
71	Godrej Ezee	godrej-ezee	Godrej_Ezee.jpg		EZE	2019-01-08 13:54:27.756459+00	2019-01-09 10:35:22.38275+00	1	4
4	Godrej	godrej	Godrej.jpg		GOD	2019-01-08 07:25:52.823713+00	2019-01-09 10:35:41.210829+00	1	\N
70	Hair & Care	hair-care	hair_care.jpg		HNC	2019-01-08 13:54:05.131134+00	2019-01-09 10:35:58.734887+00	1	6
68	Herbo	herbo	harbowash.jpg		HER	2019-01-08 13:52:09.921457+00	2019-01-09 10:36:30.676042+00	1	54
69	Head & Shoulders	head-shoulders	head_shoulder.jpg		HNS	2019-01-08 13:53:17.526032+00	2019-01-09 10:36:48.377359+00	1	56
66	Pantene	pantene	pantene.jpg		PAN	2019-01-08 13:49:53.927313+00	2019-01-09 10:37:05.639223+00	1	56
54	Patanjali	patanjali	patanjali.jpg		PAT	2019-01-08 13:41:40.881745+00	2019-01-09 10:37:23.199521+00	1	\N
65	PEPSODENT	pepsodent	pepsodent.jpg		PEP	2019-01-08 13:49:20.285317+00	2019-01-09 10:37:37.688961+00	1	5
64	Revive	revive	revive.jpg		REV	2019-01-08 13:48:54.963958+00	2019-01-09 10:37:57.653228+00	1	6
58	Set Wet	set-wet	setwet.jpg		SWT	2019-01-08 13:45:00.722061+00	2019-01-09 10:38:23.300725+00	1	6
62	SURF EXCEL	surf-excel	surf.jpg		SRF	2019-01-08 13:47:31.375142+00	2019-01-09 10:38:40.545567+00	1	5
61	Vanish	vanish	vanish.jpg		VAN	2019-01-08 13:46:51.1267+00	2019-01-09 10:39:04.836808+00	1	7
60	VIM BAR	vim-bar	vimbar.jpg		VIM	2019-01-08 13:46:11.103119+00	2019-01-09 10:39:28.81216+00	1	5
59	Whisper	whisper	whisper.jpg		WSP	2019-01-08 13:45:49.878879+00	2019-01-09 10:39:45.716595+00	1	56
5	HUL	hul	hulGF.jpg		HUL	2019-01-08 07:26:24.968116+00	2019-01-09 12:25:00.462354+00	1	\N
31	Lizol	lizol	lizolGF.jpg		LIZ	2019-01-08 11:31:36.493742+00	2019-01-09 12:25:49.152178+00	1	7
27	Nihar	nihar	nihar02.jpg		NIH	2019-01-08 11:29:17.351625+00	2019-01-09 12:26:17.972964+00	1	6
12	Odonil	odonil	odonilGF.jpg		DOD	2019-01-08 11:18:48.912549+00	2019-01-09 12:26:30.116479+00	1	1
28	Parachute	parachute	nre.jpg		PAR	2019-01-08 11:29:36.318737+00	2019-01-09 12:34:57.152915+00	1	6
40	Sunfeast	sunfeast	sunfeast02.jpg		SNF	2019-01-08 13:20:43.043752+00	2019-01-09 12:45:14.469648+00	1	39
83	Vivel	vivel	vevil02.jpg		VIV	2019-01-08 14:05:05.781798+00	2019-01-09 12:45:26.70222+00	1	39
67	Lal Dant Manjan	lal-dant-manjan	dabur_lal02.jpg		RED	2019-01-08 13:51:25.715146+00	2019-01-10 04:58:34.764765+00	1	1
86	Cocacola	cocacola	Coca-Cola-Logo.png		COL	2019-01-09 10:44:50.759306+00	2019-01-09 10:44:50.759341+00	1	\N
87	FERRERO	ferrero	ferrero.png		FER	2019-01-09 10:45:18.771174+00	2019-01-09 10:45:18.77121+00	1	\N
85	Pepsico	pepsico	pepsico.jpg		PCO	2019-01-09 10:40:35.532345+00	2019-01-09 10:51:23.740188+00	1	\N
88	LIMCA	limca	Limca_Logo.png		LIM	2019-01-09 10:53:04.999489+00	2019-01-09 10:53:04.999521+00	1	86
89	SPRITE	sprite	Sprite_Logo.jpg		SPR	2019-01-09 10:58:05.214505+00	2019-01-09 10:58:05.214539+00	1	86
90	COKE	COKE	Coca-Cola-Logo.png		COC	2019-01-09 10:58:27.619896+00	2019-01-09 10:58:51.131313+00	1	\N
91	FANTA	fanta	Fanta_Logo.png		FAN	2019-01-09 10:59:06.698691+00	2019-01-09 10:59:06.698726+00	1	\N
92	THUMS UP	thums	Thums_up_logo.jpg		THU	2019-01-09 10:59:28.222548+00	2019-01-09 10:59:28.222583+00	1	\N
93	KINDER JOY	kinder-joy	KJ_Logo.png		KIJ	2019-01-09 11:00:11.788573+00	2019-01-09 11:00:11.788607+00	1	87
94	TIC TAC	tic-tac	Tic_Tac_logo.png		TIC	2019-01-09 11:00:43.659517+00	2019-01-09 11:00:43.659548+00	1	87
95	MOUNTAIN DEW	mountain-dew	Mountain_Dew_Logo.png		MDE	2019-01-09 11:01:03.884584+00	2019-01-09 11:01:03.884618+00	1	\N
96	MIRINDA	mirinda	Mirinda_Logo.jpg		MIR	2019-01-09 11:01:53.677009+00	2019-01-09 11:04:03.437604+00	1	85
97	PEPSI	pepsi	Pepsi_logo.png		PSI	2019-01-09 11:04:30.874069+00	2019-01-09 11:04:30.874102+00	1	85
98	PEPSI BLACK	pepsi-black	Pepsi_black_logo.png		PBL	2019-01-09 11:05:31.023499+00	2019-01-09 11:05:31.023533+00	1	85
99	REAL JUICE	real-juice	Real_juice_logo.jpg		REL	2019-01-09 11:15:33.036639+00	2019-01-09 11:15:33.036672+00	1	1
100	TAAZA TEA	taaza-tea	Taaza_tea_logo.jpg		TAZ	2019-01-09 11:16:47.416457+00	2019-01-09 11:16:47.416492+00	1	\N
101	BRU COFFEE	bru-coffee	Bru_Logo.png		BRU	2019-01-09 11:17:50.628597+00	2019-01-09 11:17:50.628629+00	1	5
102	KIT KAT	kit-kat	Kit_Kat_logo.png		KIT	2019-01-09 11:18:22.002506+00	2019-01-09 11:18:22.002542+00	1	34
103	MUNCH	munch	Munch_Logo.jpg		MUN	2019-01-09 11:18:43.241491+00	2019-01-09 11:18:43.241523+00	1	34
104	NESCAFE	nescafe	Nescafe_logo.png		NCF	2019-01-09 11:19:10.520511+00	2019-01-09 11:19:10.520545+00	1	34
106	MAAZA	maaza	maaza_logo.jpg		MAZ	2019-01-09 11:36:46.770951+00	2019-01-09 11:36:46.770986+00	1	86
107	SLICE	slice	slice_logo.jpg		SLI	2019-01-09 11:37:08.376255+00	2019-01-09 11:37:08.376286+00	1	85
108	Adani Wilmar	adani-wilmar	adani_wilmar_brand_logo.png		AWI	2019-01-09 12:13:51.718246+00	2019-01-09 12:13:51.718281+00	1	\N
109	Fortune	fortune	Fortune_logo.png		FOR	2019-01-09 12:14:28.074068+00	2019-01-09 12:14:28.074103+00	1	108
110	Raag Gold	raag-gold	raag_logo.jpg		RAG	2019-01-09 12:15:02.998972+00	2019-01-09 12:15:02.999005+00	1	108
111	Amul	amul	Amul.png		AMU	2019-01-09 12:15:48.856312+00	2019-01-09 12:15:48.856348+00	1	\N
112	Aashirvaad	aashirvaad	aashirwaad.png		AAS	2019-01-09 12:17:00.730341+00	2019-01-09 12:17:00.730377+00	1	39
113	Saffola Oil	saffola-oil	saffola_logo.jpg		SOI	2019-01-09 12:17:45.946211+00	2019-01-09 12:17:45.946245+00	1	6
114	Ruchi Soya Ltd	ruchi-soya-ltd	ruchi_logo.jpg		RUL	2019-01-09 12:20:20.570451+00	2019-01-09 12:20:20.570483+00	1	\N
115	Mahakosh	mahakosh	mahakosh_logo.jpg		MAH	2019-01-09 12:20:51.011211+00	2019-01-09 12:20:51.011243+00	1	114
116	Ruchi Gold	ruchi-gold	ruchi_gold_logo.jpg		RUG	2019-01-09 12:22:54.847325+00	2019-01-09 12:22:54.847358+00	1	114
117	Madhusudan	madhusudan	madhusudan_logo.png		MAD	2019-01-09 12:23:50.605218+00	2019-01-09 12:23:50.605251+00	1	\N
118	Uttam Sugar	uttam-sugar	uttam_sugar_logo.jpg		UTS	2019-01-09 12:24:18.131257+00	2019-01-09 12:24:18.131289+00	1	\N
6	Marico	marico	marco_logoGF.jpg		MRC	2019-01-08 07:26:53.86477+00	2019-01-09 12:26:06.802419+00	1	\N
119	Tropicana	tropicana	Tropicana_logo.png		TRO	2019-01-09 12:28:22.45159+00	2019-01-09 12:28:22.45162+00	1	85
105	RED LABEL	red-label	Red_label02GF.jpg		RED	2019-01-09 11:36:14.612942+00	2019-01-09 12:45:01.643817+00	1	5
\.


--
-- Data for Name: brand_branddata; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.brand_branddata (id, brand_data_order, brand_data_id, slot_id) FROM stdin;
13	13	7	1
14	14	6	1
15	15	5	1
16	16	4	1
17	17	3	1
18	18	2	1
19	19	1	1
34	20	50	1
35	21	39	1
36	22	34	1
\.


--
-- Data for Name: brand_brandposition; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.brand_brandposition (id, position_name, brand_position_order) FROM stdin;
1	HomePage	1
\.


--
-- Data for Name: brand_vendor; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.brand_vendor (id, company_name, vendor_name, contact_person_name, telephone_no, mobile, designation, address_line1, pincode, payment_terms, vendor_registion_free, sku_listing_free, return_policy, "GST_number", "MSMED_reg_no", "MSMED_reg_document", fssai_licence, "GST_document", pan_card, cancelled_cheque, "list_of_sku_in_NPI_formate", vendor_form, vendor_products_csv, city_id, state_id) FROM stdin;
1	Testing	RAJ-Testing	\N	8510949064	8750858087	Owner	B-16 Sector-7 Noida,Dist. Gautam Budh Nagar	201301		\N	\N		asbashdkjasfhk	\N			vendor/gst_doc/Marico_Logo.png	vendor/pan_card/Set_Wet.jpg	vendor/cancelled_cheque/Marico_Logo.png			vendor/vendor_products_csv/08_Jan_19_05_37product_list.csv	1	1
2	Varun Enterprise	Varun	\N	\N	8596256314	head	sector 34,gurgaon	147850		\N	\N		8596	\N			vendor/gst_doc/-haldiram-bhujia-400gm.jpg	vendor/pan_card/1.jpg	vendor/cancelled_cheque/-haldiram-bhujia-400gm.jpg				4	2
\.


--
-- Data for Name: categories_category; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.categories_category (id, category_name, category_slug, category_desc, category_sku_part, category_image, is_created, is_modified, status, category_parent_id) FROM stdin;
4	Hair Care	hair-care		HRC		2019-01-08 05:07:14.222302+00	2019-01-08 05:07:14.222328+00	t	2
5	Oral Care	oral-care		ORC		2019-01-08 05:07:35.637904+00	2019-01-08 05:07:35.637927+00	t	2
6	Glass Cleaner	glass-cleaner		GLC		2019-01-08 05:07:57.488444+00	2019-01-08 05:07:57.488467+00	t	1
7	Hand Wash & Sanitizer	hand-wash-sanitizer		HWS		2019-01-08 05:08:16.154634+00	2019-01-08 05:08:16.154658+00	t	2
8	Bathing Bar & Soaps	bathing-bar-soaps		BBS		2019-01-08 05:08:33.184122+00	2019-01-08 05:08:33.18415+00	t	2
9	Shaving Needs	shaving-needs		SVN		2019-01-08 05:08:55.889458+00	2019-01-08 05:08:55.889485+00	t	2
10	Dishwash	dishwash		DWS		2019-01-08 05:09:16.40865+00	2019-01-08 05:09:16.408682+00	t	1
11	DEOS	deos		DEO		2019-01-08 05:09:34.539267+00	2019-01-08 05:09:34.539291+00	t	2
12	Skin Care	skin-care		SKC		2019-01-08 05:09:55.073826+00	2019-01-08 05:09:55.073851+00	t	2
13	Detergents	detergents		DET		2019-01-08 05:10:15.185414+00	2019-01-08 05:10:15.18544+00	t	1
14	Mosquito Repellent	mosquito-repellent		MQR		2019-01-08 05:10:37.144327+00	2019-01-08 05:10:37.144357+00	t	1
16	Everyday Medicine	everyday-medicine		EVM		2019-01-08 05:11:17.390466+00	2019-01-08 05:11:17.390493+00	t	2
19	Hair Removal	hair-removal		HRM		2019-01-08 05:12:10.218502+00	2019-01-08 05:12:10.218526+00	t	2
20	Sanitary Pad	sanitary-pad		SNT		2019-01-08 05:12:26.340964+00	2019-01-08 05:12:26.340983+00	t	2
21	Snacks and Branded Foods	snacks-and-branded-foods		SBF		2019-01-08 06:02:37.32116+00	2019-01-08 06:02:37.321179+00	t	\N
22	Noodles Pasta Vermicelli	noodles-pasta-vermicelli		NPV		2019-01-08 06:04:00.685908+00	2019-01-08 06:04:00.685936+00	t	21
23	Ketchup, Spreads and Condiments	ketchup-spreads-and-condiments		KSC		2019-01-08 06:04:54.250782+00	2019-01-08 06:04:54.250806+00	t	21
25	Powdered Mik	powdered-mik		PWM		2019-01-08 06:07:22.370423+00	2019-01-08 06:07:22.370447+00	t	24
26	Infant Nutrition	infant-nutrition		INF		2019-01-08 06:08:21.370844+00	2019-01-08 06:08:21.370871+00	t	\N
27	Baby Foods	baby-foods		BBF		2019-01-08 06:08:37.764069+00	2019-01-08 06:08:37.764094+00	t	26
28	Biscuits and Cookies	biscuits-and-cookies		BAC		2019-01-08 06:09:09.428048+00	2019-01-08 06:09:09.428078+00	t	21
29	Chips and Namkeen	chips-and-namkeen		CNN		2019-01-08 06:09:50.170089+00	2019-01-08 06:09:50.170113+00	t	21
30	Breakfast Cereals	breakfast-cereals		BFC		2019-01-08 06:10:18.526912+00	2019-01-08 06:10:18.526938+00	t	21
24	Dairy	dairy		DAY	category_img_file/ic_confectioneries.svg	2019-01-08 06:06:43.171927+00	2019-01-08 12:31:18.955435+00	t	\N
18	Baby Care	baby-care		BBC	category_img_file/ic_health_care.svg	2019-01-08 05:11:55.091116+00	2019-01-08 12:31:50.102196+00	t	2
17	Room Freshers	room-freshers		FRS	category_img_file/ic_instant_food.svg	2019-01-08 05:11:39.25055+00	2019-01-08 12:32:25.537325+00	t	1
15	Bathroom & Toilet Cleaner	bathroom-toilet-cleaner		BTC	category_img_file/ic_beverage.svg	2019-01-08 05:11:00.73057+00	2019-01-08 12:43:12.853088+00	t	1
31	Staples	staples		STP		2019-01-09 07:12:18.576188+00	2019-01-09 07:12:18.576213+00	t	\N
1	Household Needs	household-needs		HLD	category_img_file/ic_home_kitchen.svg	2019-01-08 05:04:01.513646+00	2019-01-09 07:33:12.7434+00	t	\N
2	Personal Care	personal-care		PCR	category_img_file/ic_personal_care.svg	2019-01-08 05:05:26.653662+00	2019-01-09 07:34:10.703856+00	t	\N
3	Shoe Care	shoe-care		SHC	category_img_file/ic_baby_care.svg	2019-01-08 05:06:25.224046+00	2019-01-09 07:36:36.99784+00	t	1
32	Oil & Ghee	oil-ghee		OIL		2019-01-09 07:38:20.076291+00	2019-01-09 07:38:20.07632+00	t	31
33	Butter, Cream & Cheese	butter-cream-cheese		BUT		2019-01-09 07:42:01.401662+00	2019-01-09 07:42:01.401686+00	t	24
34	Foodgrains & Flour	foodgrains-flour		FOG		2019-01-09 07:42:46.742982+00	2019-01-09 07:42:46.743008+00	t	31
35	Sugar & Salts	sugar-salts		SUG		2019-01-09 07:43:26.266429+00	2019-01-09 07:43:26.266456+00	t	31
37	Soft Drink	soft-drink		CSD		2019-01-09 12:02:39.014388+00	2019-01-09 12:02:39.014417+00	t	36
38	Juices	juices		JUI		2019-01-09 12:03:13.359811+00	2019-01-09 12:03:13.359838+00	t	36
39	Tea	tea		TEA		2019-01-09 12:03:32.49342+00	2019-01-09 12:03:32.493448+00	t	36
40	Coffee	coffee		COF		2019-01-09 12:03:47.462354+00	2019-01-09 12:03:47.46238+00	t	36
41	Confectionery	confectionery		CON		2019-01-09 12:04:07.64539+00	2019-01-09 12:04:07.64542+00	t	\N
42	Chocolate	chocolate		CHO		2019-01-09 12:04:19.146771+00	2019-01-09 12:04:19.1468+00	t	41
43	Candy	candy		CAN		2019-01-09 12:04:38.568609+00	2019-01-09 12:04:38.568639+00	t	41
36	Beverages	beverages		BEV		2019-01-09 12:01:57.711974+00	2019-01-09 12:04:59.160349+00	t	\N
\.


--
-- Data for Name: categories_categorydata; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.categories_categorydata (id, category_data_order, category_data_id, category_pos_id) FROM stdin;
1	1	15	1
12	2	1	1
13	3	2	1
\.


--
-- Data for Name: categories_categoryposation; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.categories_categoryposation (id, posation_name, category_posation_order) FROM stdin;
1	home-category	1
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
1	2019-01-07 16:36:00.046599+00	1	9911703645	2	[{"changed": {"fields": ["first_name", "last_name"]}}]	14	1
2	2019-01-07 16:36:59.733974+00	2	8750858087	1	[{"added": {}}]	14	1
3	2019-01-07 16:37:17.855984+00	2	8750858087	2	[{"changed": {"fields": ["first_name", "last_name", "is_staff", "is_superuser"]}}]	14	1
4	2019-01-08 05:04:01.51652+00	1	Household Needs	1	[{"added": {}}]	18	2
5	2019-01-08 05:05:26.655154+00	2	Personal Care	1	[{"added": {}}]	18	2
6	2019-01-08 05:06:25.225541+00	3	Household Needs -> Shoe Care	1	[{"added": {}}]	18	2
7	2019-01-08 05:07:14.223828+00	4	Personal Care -> Hair Care	1	[{"added": {}}]	18	2
8	2019-01-08 05:07:35.639354+00	5	Personal Care -> Oral Care	1	[{"added": {}}]	18	2
9	2019-01-08 05:07:57.489859+00	6	Household Needs -> Glass Cleaner	1	[{"added": {}}]	18	2
10	2019-01-08 05:08:16.156029+00	7	Personal Care -> Hand Wash & Sanitizer	1	[{"added": {}}]	18	2
11	2019-01-08 05:08:33.185611+00	8	Personal Care -> Bathing Bar & Soaps	1	[{"added": {}}]	18	2
12	2019-01-08 05:08:55.890988+00	9	Personal Care -> Shaving Needs	1	[{"added": {}}]	18	2
13	2019-01-08 05:09:16.410125+00	10	Household Needs -> Dishwash	1	[{"added": {}}]	18	2
14	2019-01-08 05:09:34.5407+00	11	Personal Care -> DEOS	1	[{"added": {}}]	18	2
15	2019-01-08 05:09:55.075305+00	12	Personal Care -> Skin Care	1	[{"added": {}}]	18	2
16	2019-01-08 05:10:15.186823+00	13	Household Needs -> Detergents	1	[{"added": {}}]	18	2
17	2019-01-08 05:10:37.145833+00	14	Household Needs -> Mosquito Repellent	1	[{"added": {}}]	18	2
18	2019-01-08 05:11:00.73205+00	15	Household Needs -> Bathroom & Toilet Cleaner	1	[{"added": {}}]	18	2
19	2019-01-08 05:11:17.391913+00	16	Personal Care -> Everyday Medicine	1	[{"added": {}}]	18	2
20	2019-01-08 05:11:39.251983+00	17	Household Needs -> Room Freshers	1	[{"added": {}}]	18	2
21	2019-01-08 05:11:55.092599+00	18	Personal Care -> Baby Care	1	[{"added": {}}]	18	2
22	2019-01-08 05:12:10.219967+00	19	Personal Care -> Hair Removal	1	[{"added": {}}]	18	2
23	2019-01-08 05:12:26.342367+00	20	Personal Care -> Sanitary Pad	1	[{"added": {}}]	18	2
24	2019-01-08 05:20:55.581567+00	1	GST-0	1	[{"added": {}}]	31	2
25	2019-01-08 05:21:17.371334+00	2	GST-5	1	[{"added": {}}]	31	2
26	2019-01-08 05:21:38.663645+00	3	GST-12	1	[{"added": {}}]	31	2
27	2019-01-08 05:21:59.692923+00	4	GST-18	1	[{"added": {}}]	31	2
28	2019-01-08 06:02:37.322633+00	21	Snacks and Branded Foods	1	[{"added": {}}]	18	2
29	2019-01-08 06:04:00.687408+00	22	Snacks and Branded Foods -> Noodles Pasta Vermicelli	1	[{"added": {}}]	18	2
30	2019-01-08 06:04:54.252261+00	23	Snacks and Branded Foods -> Ketchup, Spreads and Condiments	1	[{"added": {}}]	18	2
31	2019-01-08 06:06:43.17333+00	24	Dairy	1	[{"added": {}}]	18	2
32	2019-01-08 06:07:22.371839+00	25	Dairy -> Powdered Mik	1	[{"added": {}}]	18	2
33	2019-01-08 06:08:21.372364+00	26	Infant Nutrition	1	[{"added": {}}]	18	2
34	2019-01-08 06:08:37.765457+00	27	Infant Nutrition -> Baby Foods	1	[{"added": {}}]	18	2
35	2019-01-08 06:09:09.429484+00	28	Snacks and Branded Foods -> Biscuits and Cookies	1	[{"added": {}}]	18	2
36	2019-01-08 06:09:50.171534+00	29	Snacks and Branded Foods -> Chips and Namkeen	1	[{"added": {}}]	18	2
37	2019-01-08 06:10:18.528464+00	30	Snacks and Branded Foods -> Breakfast Cereals	1	[{"added": {}}]	18	2
38	2019-01-08 06:35:02.255627+00	3	8567075678	1	[{"added": {}}]	14	1
39	2019-01-08 06:35:39.198066+00	3	8567075678	2	[{"changed": {"fields": ["first_name", "last_name", "user_type", "is_superuser"]}}]	14	1
40	2019-01-08 06:40:07.966233+00	3	8567075678	3		14	1
41	2019-01-08 06:40:25.277577+00	4	8567075678	1	[{"added": {}}]	14	1
42	2019-01-08 06:40:41.422838+00	4	8567075678	2	[{"changed": {"fields": ["first_name", "last_name", "user_type", "is_superuser"]}}]	14	1
43	2019-01-08 07:24:36.97622+00	1	Dabur	1	[{"added": {}}]	51	2
44	2019-01-08 07:25:00.362685+00	2	Fena	1	[{"added": {}}]	51	2
45	2019-01-08 07:25:34.609347+00	3	Ghadi	1	[{"added": {}}]	51	2
46	2019-01-08 07:25:52.826471+00	4	Godrej	1	[{"added": {}}]	51	2
47	2019-01-08 07:26:24.970814+00	5	HUL	1	[{"added": {}}]	51	2
48	2019-01-08 07:26:53.867503+00	6	Marico	1	[{"added": {}}]	51	2
49	2019-01-08 07:27:20.96763+00	7	Reckitt Benckiser	1	[{"added": {}}]	51	2
50	2019-01-08 07:28:42.493951+00	8	Reckitt Benckiser -> Harpic	1	[{"added": {}}]	51	2
51	2019-01-08 08:18:54.074811+00	14	Harpic Powerplus Toilet Cleaner Rose, 1 L all in one(MRP-160)	3		36	1
52	2019-01-08 08:18:54.079767+00	13	Harpic Powerplus Toilet Cleaner Orange, 1 l(MRP-160)	3		36	1
53	2019-01-08 08:18:54.083447+00	12	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-168)	3		36	1
54	2019-01-08 08:18:54.087154+00	11	Harpic Powerplus Toilet Cleaner Orange, 500 ml(MRP-82)	3		36	1
55	2019-01-08 08:18:54.090745+00	10	Harpic Powerplus Toilet Cleaner Original, 500 ml+ 30 Extra(MRP-82)	3		36	1
56	2019-01-08 08:18:54.0944+00	9	Harpic Powerplus Toilet Cleaner Original, 500 ml(MRP-82)	3		36	1
57	2019-01-08 08:18:54.098058+00	8	Harpic Powerplus Toilet Cleaner Rose, 1 L(MRP-156)	3		36	1
58	2019-01-08 08:18:54.10163+00	7	Harpic Fresh Toilet Cleaner Citrus, 500 ml(MRP-80)	3		36	1
59	2019-01-08 08:18:54.105122+00	6	Harpic Fresh Toilet Cleaner Pine, 500 ml(MRP-78)	3		36	1
60	2019-01-08 08:18:54.108593+00	5	Harpic Bathroom Cleaner - Lemon - 500 ml(MRP-84)	3		36	1
61	2019-01-08 08:18:54.111987+00	4	Harpic Bathroom Cleaner Floral - 500 ml(MRP-84)	3		36	1
62	2019-01-08 08:18:54.115521+00	3	Harpic Powerplus Original, 200 ml(MRP-36)	3		36	1
63	2019-01-08 08:18:54.118961+00	2	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-164)	3		36	1
64	2019-01-08 08:18:54.12257+00	1	fortune sunflowers oil	3		36	1
65	2019-01-08 08:23:59.816733+00	27	Harpic Powerplus Toilet Cleaner Rose, 1 L all in one(MRP-160)	3		36	2
66	2019-01-08 08:23:59.821682+00	26	Harpic Powerplus Toilet Cleaner Orange, 1 l(MRP-160)	3		36	2
67	2019-01-08 08:23:59.825307+00	25	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-168)	3		36	2
68	2019-01-08 08:23:59.828967+00	24	Harpic Powerplus Toilet Cleaner Orange, 500 ml(MRP-82)	3		36	2
69	2019-01-08 08:23:59.834738+00	23	Harpic Powerplus Toilet Cleaner Original, 500 ml+ 30 Extra(MRP-82)	3		36	2
70	2019-01-08 08:23:59.8383+00	22	Harpic Powerplus Toilet Cleaner Original, 500 ml(MRP-82)	3		36	2
71	2019-01-08 08:23:59.841945+00	21	Harpic Powerplus Toilet Cleaner Rose, 1 L(MRP-156)	3		36	2
72	2019-01-08 08:23:59.845474+00	20	Harpic Fresh Toilet Cleaner Citrus, 500 ml(MRP-80)	3		36	2
73	2019-01-08 08:23:59.849205+00	19	Harpic Fresh Toilet Cleaner Pine, 500 ml(MRP-78)	3		36	2
74	2019-01-08 08:23:59.8529+00	18	Harpic Bathroom Cleaner - Lemon - 500 ml(MRP-84)	3		36	2
75	2019-01-08 08:23:59.856526+00	17	Harpic Bathroom Cleaner Floral - 500 ml(MRP-84)	3		36	2
76	2019-01-08 08:23:59.860116+00	16	Harpic Powerplus Original, 200 ml(MRP-36)	3		36	2
77	2019-01-08 08:23:59.863888+00	15	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-164)	3		36	2
78	2019-01-08 11:17:40.557421+00	9	Dabur -> Dabur Amla	1	[{"added": {}}]	51	2
79	2019-01-08 11:18:03.796266+00	10	Dabur -> Dabur Red	1	[{"added": {}}]	51	2
80	2019-01-08 11:18:25.670579+00	11	Dabur -> Meswak	1	[{"added": {}}]	51	2
81	2019-01-08 11:18:48.914494+00	12	Dabur -> Odonil	1	[{"added": {}}]	51	2
82	2019-01-08 11:19:17.891287+00	13	Fena -> NIP	1	[{"added": {}}]	51	2
83	2019-01-08 11:19:38.900595+00	14	Godrej -> Godrej Expert	1	[{"added": {}}]	51	2
84	2019-01-08 11:20:06.125677+00	15	Godrej -> Godrej No. 1	1	[{"added": {}}]	51	2
85	2019-01-08 11:20:29.762902+00	16	Godrej -> Godrej Nupur	1	[{"added": {}}]	51	2
86	2019-01-08 11:21:22.997694+00	17	Godrej -> Good knight	1	[{"added": {}}]	51	2
87	2019-01-08 11:22:09.283571+00	18	HUL -> DOVE	1	[{"added": {}}]	51	2
88	2019-01-08 11:23:22.209038+00	19	HUL -> FAIR & LOVELY	1	[{"added": {}}]	51	2
89	2019-01-08 11:23:51.239+00	20	HUL -> Lifebuoy	1	[{"added": {}}]	51	2
90	2019-01-08 11:24:57.614693+00	21	HUL -> LUX	1	[{"added": {}}]	51	2
91	2019-01-08 11:26:25.04328+00	22	HUL -> PONDS	1	[{"added": {}}]	51	2
92	2019-01-08 11:26:51.768698+00	23	HUL -> RIN	1	[{"added": {}}]	51	2
93	2019-01-08 11:28:21.409764+00	24	HUL -> TRESEMME	1	[{"added": {}}]	51	2
94	2019-01-08 11:28:38.054398+00	25	HUL -> VASELINE	1	[{"added": {}}]	51	2
95	2019-01-08 11:28:56.128356+00	26	HUL -> Wheel	1	[{"added": {}}]	51	2
96	2019-01-08 11:29:17.353492+00	27	Marico -> Nihar	1	[{"added": {}}]	51	2
97	2019-01-08 11:29:36.320623+00	28	Marico -> Parachute	1	[{"added": {}}]	51	2
98	2019-01-08 11:30:39.097413+00	29	Reckitt Benckiser -> Cherry Blossom	1	[{"added": {}}]	51	2
99	2019-01-08 11:30:57.083499+00	30	Reckitt Benckiser -> Dettol	1	[{"added": {}}]	51	2
100	2019-01-08 11:31:36.49559+00	31	Reckitt Benckiser -> Lizol	1	[{"added": {}}]	51	2
101	2019-01-08 11:31:55.026655+00	32	Reckitt Benckiser -> Moov	1	[{"added": {}}]	51	2
102	2019-01-08 11:33:14.617721+00	33	Reckitt Benckiser -> Veet	1	[{"added": {}}]	51	2
103	2019-01-08 11:43:15.45402+00	1	India	1	[{"added": {}}]	22	2
104	2019-01-08 11:43:34.692867+00	1	Uttar Pradesh	1	[{"added": {}}]	21	2
105	2019-01-08 11:43:51.943649+00	1	Noida	1	[{"added": {}}]	20	2
106	2019-01-08 11:44:44.784985+00	1	gm	1	[{"added": {}}]	49	2
107	2019-01-08 11:44:46.891861+00	1	Gram Factory - gm	1	[{"added": {}}]	47	2
108	2019-01-08 11:45:32.208167+00	1	Gramfactory-Noida - Gram Factory	1	[{"added": {}}, {"added": {"name": "address", "object": "Greater Noida"}}]	44	2
109	2019-01-08 11:45:53.897262+00	1	Gramfactory-Noida - Gram Factory	2	[{"changed": {"fields": ["status"]}}]	44	2
110	2019-01-08 12:07:51.223841+00	1	RAJ-Testing	1	[{"added": {}}]	52	2
111	2019-01-08 12:09:40.743303+00	1	Gramfactory-Noida - Gram Factory	2	[{"added": {"name": "address", "object": "GN-BIlling"}}]	44	2
112	2019-01-08 12:11:05.608016+00	1	Cart object (1)	1	[{"added": {}}, {"added": {"name": "Select Product", "object": "Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-164)"}}, {"added": {"name": "Select Product", "object": "Harpic Powerplus Original, 200 ml(MRP-36)"}}, {"added": {"name": "Select Product", "object": "Harpic Bathroom Cleaner - Lemon - 500 ml(MRP-84)"}}]	65	2
113	2019-01-08 12:11:21.143918+00	1	Cart object (1)	2	[]	65	2
114	2019-01-08 12:13:06.547434+00	1	18-19/1	1	[{"added": {}}, {"added": {"name": "grn order product mapping", "object": "GRNOrderProductMapping object (1)"}}, {"added": {"name": "grn order product mapping", "object": "GRNOrderProductMapping object (2)"}}, {"added": {"name": "grn order product mapping", "object": "GRNOrderProductMapping object (3)"}}]	69	2
115	2019-01-08 12:16:42.372931+00	1	banner_78.png	1	[{"added": {}}]	56	1
116	2019-01-08 12:17:50.056498+00	2	banner_I6.png	1	[{"added": {}}]	56	1
117	2019-01-08 12:18:13.233486+00	1	HomePage	1	[{"added": {}}]	54	1
118	2019-01-08 12:18:35.108645+00	1	HomePage->homepage-slot1	1	[{"added": {}}]	57	1
119	2019-01-08 12:18:40.093027+00	1	HomePage-homepage-slot1	1	[{"added": {}}, {"added": {"name": "banner data", "object": "Marico"}}, {"added": {"name": "banner data", "object": "Goldee"}}]	55	1
120	2019-01-08 12:22:58.485742+00	1	HomePage	1	[{"added": {}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}]	50	1
121	2019-01-08 12:24:43.661256+00	1	HomePage	2	[{"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}, {"added": {"name": "brand data", "object": "HomePage"}}]	50	1
122	2019-01-08 12:25:10.894118+00	1	home-category	1	[{"added": {}}]	16	1
123	2019-01-08 12:26:26.649988+00	2	Personal Care	2	[{"changed": {"fields": ["category_image"]}}]	18	1
124	2019-01-08 12:27:13.256213+00	2	Personal Care	2	[]	18	1
125	2019-01-08 12:29:24.320991+00	1	home-category	2	[{"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}, {"added": {"name": "category data", "object": "home-category"}}]	16	1
126	2019-01-08 12:29:36.767963+00	2	Arzoo Apartment Shop - Gram Factory	2	[{"changed": {"fields": ["status"]}}]	44	1
127	2019-01-08 12:30:54.29822+00	15	Household Needs -> Bathroom & Toilet Cleaner	2	[{"changed": {"fields": ["category_image"]}}]	18	1
128	2019-01-08 12:31:18.958079+00	24	Dairy	2	[{"changed": {"fields": ["category_image"]}}]	18	1
129	2019-01-08 12:31:50.10466+00	18	Personal Care -> Baby Care	2	[{"changed": {"fields": ["category_image"]}}]	18	1
130	2019-01-08 12:32:25.540181+00	17	Household Needs -> Room Freshers	2	[{"changed": {"fields": ["category_image"]}}]	18	1
131	2019-01-08 12:33:51.394544+00	1	home-category	2	[{"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}, {"deleted": {"name": "category data", "object": "home-category"}}]	16	1
132	2019-01-08 12:35:36.445117+00	1	home-category	2	[{"added": {"name": "category data", "object": "home-category"}}]	16	1
133	2019-01-08 12:39:42.871653+00	3	baniya general store - Gram Factory	2	[{"changed": {"fields": ["status"]}}]	44	1
134	2019-01-08 12:40:55.582155+00	1	HomePage	2	[{"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}, {"deleted": {"name": "brand data", "object": "HomePage"}}]	50	1
135	2019-01-08 12:40:59.26257+00	1	gm	2	[]	49	1
136	2019-01-08 12:41:01.234065+00	1	Retailer - gm	2	[{"changed": {"fields": ["shop_type"]}}]	47	1
137	2019-01-08 12:41:11.310844+00	2	Gram Factory - gm	1	[{"added": {}}]	47	1
138	2019-01-08 12:41:23.765678+00	1	Gramfactory-Noida - Gram Factory	2	[{"changed": {"fields": ["shop_type"]}}]	44	1
139	2019-01-08 12:42:01.119213+00	1	baniya general store(Retailer - gm) --mapped to-- Gramfactory-Noida(Gram Factory - gm)(Active)	1	[{"added": {}}]	46	1
140	2019-01-08 12:43:01.548243+00	1	home-category	2	[{"deleted": {"name": "category data", "object": "home-category"}}]	16	1
141	2019-01-08 12:43:12.855014+00	15	Household Needs -> Bathroom & Toilet Cleaner	2	[]	18	1
142	2019-01-08 12:47:56.674703+00	2	18-19/2	1	[{"added": {}}, {"added": {"name": "grn order product mapping", "object": "GRNOrderProductMapping object (4)"}}, {"added": {"name": "grn order product mapping", "object": "GRNOrderProductMapping object (5)"}}, {"added": {"name": "grn order product mapping", "object": "GRNOrderProductMapping object (6)"}}]	69	2
143	2019-01-08 12:49:06.434212+00	7	7006440794	1	[{"added": {}}]	14	1
144	2019-01-08 12:49:24.610067+00	7	7006440794	2	[{"changed": {"fields": ["is_staff", "is_superuser"]}}]	14	1
145	2019-01-08 13:17:18.305753+00	34	Nestle	1	[{"added": {}}]	51	2
146	2019-01-08 13:17:52.584945+00	35	Nestle -> Maggi	1	[{"added": {}}]	51	2
147	2019-01-08 13:18:40.31206+00	36	Nestle -> Everyday	1	[{"added": {}}]	51	2
148	2019-01-08 13:19:09.289022+00	37	Nestle -> Cerelac	1	[{"added": {}}]	51	2
149	2019-01-08 13:19:44.250283+00	38	Nestle -> Lactogen	1	[{"added": {}}]	51	2
150	2019-01-08 13:20:07.362914+00	39	ITC	1	[{"added": {}}]	51	2
151	2019-01-08 13:20:43.045718+00	40	ITC -> Sunfeast	1	[{"added": {}}]	51	2
152	2019-01-08 13:21:30.797844+00	41	ITC -> Bingo	1	[{"added": {}}]	51	2
153	2019-01-08 13:21:57.722986+00	42	ITC -> Yippee	1	[{"added": {}}]	51	2
154	2019-01-08 13:22:54.93758+00	43	Kellogg's	1	[{"added": {}}]	51	2
155	2019-01-08 13:23:25.71082+00	44	Kellogg's -> Cornflakes	1	[{"added": {}}]	51	2
156	2019-01-08 13:24:03.825369+00	45	Kellogg's -> Chocos	1	[{"added": {}}]	51	2
157	2019-01-08 13:24:41.326987+00	46	Fritolay	1	[{"added": {}}]	51	2
158	2019-01-08 13:25:17.697167+00	47	Fritolay -> Lay's	1	[{"added": {}}]	51	2
159	2019-01-08 13:25:50.516624+00	48	Fritolay -> Doritos	1	[{"added": {}}]	51	2
160	2019-01-08 13:26:29.882813+00	49	Fritolay -> Quaker	1	[{"added": {}}]	51	2
161	2019-01-08 13:27:11.98637+00	50	Haldiram	1	[{"added": {}}]	51	2
162	2019-01-08 13:28:24.220942+00	51	Haldiram -> Haldiram Snacks	1	[{"added": {}}]	51	2
163	2019-01-08 13:40:44.413856+00	52	ITC	1	[{"added": {}}]	51	2
164	2019-01-08 13:41:03.979662+00	53	P&G	1	[{"added": {}}]	51	2
165	2019-01-08 13:41:40.884556+00	54	Patanjali	1	[{"added": {}}]	51	2
166	2019-01-08 13:42:12.279168+00	53	P&G	3		51	2
167	2019-01-08 13:42:25.094159+00	52	ITC	3		51	2
168	2019-01-08 13:42:41.502657+00	55	ITC Limited	1	[{"added": {}}]	51	2
169	2019-01-08 13:42:59.39074+00	56	P&G	1	[{"added": {}}]	51	2
170	2019-01-08 13:43:19.26431+00	57	Colgate	1	[{"added": {}}]	51	2
171	2019-01-08 13:45:00.724076+00	58	Marico -> Set Wet	1	[{"added": {}}]	51	2
172	2019-01-08 13:45:49.880657+00	59	P&G -> Whisper	1	[{"added": {}}]	51	2
173	2019-01-08 13:46:11.105112+00	60	HUL -> VIM BAR	1	[{"added": {}}]	51	2
174	2019-01-08 13:46:51.128544+00	61	Reckitt Benckiser -> Vanish	1	[{"added": {}}]	51	2
175	2019-01-08 13:47:31.377539+00	62	HUL -> SURF EXCEL	1	[{"added": {}}]	51	2
176	2019-01-08 13:48:01.69729+00	63	HUL -> Sunsilk	1	[{"added": {}}]	51	2
177	2019-01-08 13:48:54.966227+00	64	Marico -> Revive	1	[{"added": {}}]	51	2
178	2019-01-08 13:49:20.287323+00	65	HUL -> PEPSODENT	1	[{"added": {}}]	51	2
179	2019-01-08 13:49:53.929213+00	66	P&G -> Pantene	1	[{"added": {}}]	51	2
180	2019-01-08 13:51:25.71796+00	67	Dabur -> Lal Dant Manjan	1	[{"added": {}}]	51	2
181	2019-01-08 13:52:09.923449+00	68	Patanjali -> Herbo	1	[{"added": {}}]	51	2
182	2019-01-08 13:53:17.52798+00	69	P&G -> Head & Shoulders	1	[{"added": {}}]	51	2
183	2019-01-08 13:54:05.133208+00	70	Marico -> Hair & Care	1	[{"added": {}}]	51	2
184	2019-01-08 13:54:27.75841+00	71	Godrej -> Godrej Ezee	1	[{"added": {}}]	51	2
185	2019-01-08 13:55:06.465947+00	72	ITC -> Engage	1	[{"added": {}}]	51	2
186	2019-01-08 13:55:27.275369+00	73	Dabur -> Dabur Almond	1	[{"added": {}}]	51	2
187	2019-01-08 13:55:46.313971+00	74	Reckitt Benckiser -> Colin	1	[{"added": {}}]	51	2
188	2019-01-08 13:56:04.569229+00	74	Reckitt Benckiser -> Colin	2	[{"changed": {"fields": ["brand_code"]}}]	51	2
189	2019-01-08 13:56:38.659207+00	75	Colgate -> Colgate_Brand	1	[{"added": {}}]	51	2
190	2019-01-08 13:57:05.324111+00	76	HUL -> CLOSE UP	1	[{"added": {}}]	51	2
191	2019-01-08 13:57:29.342514+00	77	HUL -> CLINIC PLUS	1	[{"added": {}}]	51	2
192	2019-01-08 14:02:35.265675+00	78	P&G -> Gillete	1	[{"added": {}}]	51	2
193	2019-01-08 14:02:58.720148+00	79	P&G -> Pampers	1	[{"added": {}}]	51	2
194	2019-01-08 14:03:50.197434+00	80	Reckitt Benckiser -> Robin	1	[{"added": {}}]	51	2
195	2019-01-08 14:04:13.351356+00	81	P&G -> Tide	1	[{"added": {}}]	51	2
196	2019-01-08 14:04:39.190835+00	82	P&G -> Vicks	1	[{"added": {}}]	51	2
197	2019-01-08 14:05:05.783794+00	83	ITC -> Vivel	1	[{"added": {}}]	51	2
198	2019-01-08 14:05:40.103271+00	1	HomePage	2	[{"added": {"object": "HomePage", "name": "brand data"}}, {"added": {"object": "HomePage", "name": "brand data"}}, {"added": {"object": "HomePage", "name": "brand data"}}]	50	2
199	2019-01-09 04:29:52.173303+00	84	Marico -> Saffola Oats	1	[{"added": {}}]	51	2
200	2019-01-09 06:08:06.575665+00	5	9899746673	3		14	1
201	2019-01-09 06:20:28.084111+00	3	18-19/3	1	[{"added": {}}, {"added": {"object": "GRNOrderProductMapping object (7)", "name": "grn order product mapping"}}, {"added": {"object": "GRNOrderProductMapping object (8)", "name": "grn order product mapping"}}, {"added": {"object": "GRNOrderProductMapping object (9)", "name": "grn order product mapping"}}]	69	1
202	2019-01-09 06:27:22.59842+00	4	Arzoo Apartment Shop - Retailer	2	[{"changed": {"fields": ["status"]}}]	44	1
203	2019-01-09 06:27:35.225669+00	2	Arzoo Apartment Shop(Retailer - gm) --mapped to-- Gramfactory-Noida(Gram Factory - gm)(Active)	1	[{"added": {}}]	46	1
204	2019-01-09 06:40:32.275303+00	4	18-19/4	1	[{"added": {}}, {"added": {"object": "GRNOrderProductMapping object (10)", "name": "grn order product mapping"}}, {"added": {"object": "GRNOrderProductMapping object (11)", "name": "grn order product mapping"}}, {"added": {"object": "GRNOrderProductMapping object (12)", "name": "grn order product mapping"}}]	69	1
205	2019-01-09 07:10:26.071294+00	7	7006440794	2	[{"changed": {"fields": ["first_name", "email"]}}]	14	7
206	2019-01-09 07:10:50.413425+00	7	7006440794	2	[{"changed": {"fields": ["first_name", "last_name"]}}]	14	7
207	2019-01-09 07:11:47.307377+00	9	7763886418	2	[{"changed": {"fields": ["is_staff", "is_superuser"]}}]	14	7
208	2019-01-09 07:12:14.610424+00	2	Haryana	1	[{"added": {}}]	21	7
209	2019-01-09 07:12:18.577629+00	31	Staples	1	[{"added": {}}]	18	2
210	2019-01-09 07:12:26.529409+00	3	New Delhi	1	[{"added": {}}]	21	7
211	2019-01-09 07:12:48.357278+00	2	Sonipat	1	[{"added": {}}]	20	7
212	2019-01-09 07:13:02.45445+00	3	Karol Bagh	1	[{"added": {}}]	20	7
213	2019-01-09 07:13:12.266377+00	4	Gurgaon	1	[{"added": {}}]	20	7
214	2019-01-09 07:13:28.328828+00	5	Greater Noida	1	[{"added": {}}]	20	7
215	2019-01-09 07:16:07.754024+00	5	Pal Shop - Retailer	2	[{"changed": {"fields": ["status"]}}]	44	1
216	2019-01-09 07:16:27.730797+00	2	banner_I6.png	2	[{"changed": {"fields": ["banner_start_date", "banner_end_date"]}}]	56	7
217	2019-01-09 07:16:31.411729+00	3	Pal Shop(Retailer - gm) --mapped to-- Gramfactory-Noida(Gram Factory - gm)(Active)	1	[{"added": {}}]	46	1
218	2019-01-09 07:17:01.422244+00	1	banner_78.png	2	[{"changed": {"fields": ["banner_end_date"]}}]	56	7
219	2019-01-09 07:18:03.216888+00	3	banner_56.png	1	[{"added": {}}]	56	7
220	2019-01-09 07:20:03.66864+00	4	banner_60.png	1	[{"added": {}}]	56	7
221	2019-01-09 07:22:16.248835+00	5		1	[{"added": {}}]	56	7
222	2019-01-09 07:22:39.63783+00	5	banner_24.png	2	[{"changed": {"fields": ["image"]}}]	56	7
223	2019-01-09 07:23:40.410369+00	6	banner_37.png	1	[{"added": {}}]	56	7
224	2019-01-09 07:24:17.939746+00	1	HomePage-homepage-slot1	2	[{"added": {"object": "GramFactory", "name": "banner data"}}, {"added": {"object": "lyzol", "name": "banner data"}}, {"added": {"object": "snacks", "name": "banner data"}}, {"added": {"object": "cream", "name": "banner data"}}]	55	7
225	2019-01-09 07:33:12.750119+00	1	Household Needs	2	[{"changed": {"fields": ["category_image"]}}]	18	7
226	2019-01-09 07:34:10.70579+00	2	Personal Care	2	[]	18	7
227	2019-01-09 07:34:56.516324+00	1	home-category	2	[{"added": {"object": "home-category", "name": "category data"}}, {"added": {"object": "home-category", "name": "category data"}}]	16	7
228	2019-01-09 07:35:41.672586+00	1	home-category	2	[{"changed": {"object": "home-category", "fields": ["category_data"], "name": "category data"}}, {"changed": {"object": "home-category", "fields": ["category_data"], "name": "category data"}}]	16	7
229	2019-01-09 07:36:37.000467+00	3	Household Needs -> Shoe Care	2	[{"changed": {"fields": ["category_image"]}}]	18	7
230	2019-01-09 07:38:20.077865+00	32	Staples -> Oil & Ghee	1	[{"added": {}}]	18	2
231	2019-01-09 07:42:01.403507+00	33	Dairy -> Butter, Cream & Cheese	1	[{"added": {}}]	18	2
232	2019-01-09 07:42:46.744555+00	34	Staples -> Foodgrains & Flour	1	[{"added": {}}]	18	2
233	2019-01-09 07:43:26.268027+00	35	Staples -> Sugar & Salts	1	[{"added": {}}]	18	2
234	2019-01-09 07:45:38.760483+00	342	Haldiram aloo bhuji mrp5	2	[{"added": {"name": "product image", "object": "ProductImage object (1)"}}]	36	7
235	2019-01-09 07:47:52.678988+00	343	Haldiram Bikaneri bhujia mrp5	2	[{"added": {"name": "product image", "object": "ProductImage object (2)"}}]	36	7
236	2019-01-09 07:48:36.856424+00	2	Varun	1	[{"added": {}}, {"added": {"name": "product vendor mapping", "object": "Varun"}}, {"added": {"name": "product vendor mapping", "object": "Varun"}}]	52	7
237	2019-01-09 08:03:40.769138+00	6	Nikita ki shop - Retailer	2	[{"changed": {"fields": ["status"]}}]	44	7
238	2019-01-09 08:03:42.129171+00	6	Nikita ki shop - Retailer	2	[]	44	1
239	2019-01-09 08:03:42.15911+00	4	Nikita ki shop(Retailer - gm) --mapped to-- Gramfactory-Noida(Gram Factory - gm)(Active)	1	[{"added": {}}]	46	7
240	2019-01-09 09:46:30.796815+00	11	9555072423	1	[{"added": {}}]	14	7
241	2019-01-09 09:46:41.664556+00	11	9555072423	2	[{"changed": {"fields": ["is_staff"]}}]	14	7
242	2019-01-09 09:52:29.722748+00	11	9555072423	2	[{"changed": {"fields": ["user_permissions"]}}]	14	7
243	2019-01-09 10:33:27.0544+00	77	HUL -> CLINIC PLUS	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
244	2019-01-09 10:33:52.83475+00	76	HUL -> CLOSE UP	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
245	2019-01-09 10:34:12.041167+00	75	Colgate -> Colgate_Brand	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
246	2019-01-09 10:34:22.559887+00	57	Colgate	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
247	2019-01-09 10:34:37.585476+00	74	Reckitt Benckiser -> Colin	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
248	2019-01-09 10:34:51.779904+00	73	Dabur -> Dabur Almond	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
249	2019-01-09 10:35:06.495996+00	72	ITC -> Engage	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
250	2019-01-09 10:35:22.385412+00	71	Godrej -> Godrej Ezee	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
251	2019-01-09 10:35:41.21349+00	4	Godrej	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
252	2019-01-09 10:35:58.737498+00	70	Marico -> Hair & Care	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
253	2019-01-09 10:36:30.678495+00	68	Patanjali -> Herbo	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
254	2019-01-09 10:36:48.380004+00	69	P&G -> Head & Shoulders	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
255	2019-01-09 10:37:05.641923+00	66	P&G -> Pantene	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
256	2019-01-09 10:37:23.201948+00	54	Patanjali	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
257	2019-01-09 10:37:37.69145+00	65	HUL -> PEPSODENT	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
258	2019-01-09 10:37:57.655976+00	64	Marico -> Revive	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
259	2019-01-09 10:38:23.307466+00	58	Marico -> Set Wet	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
260	2019-01-09 10:38:40.548461+00	62	HUL -> SURF EXCEL	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
261	2019-01-09 10:39:04.839452+00	61	Reckitt Benckiser -> Vanish	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
262	2019-01-09 10:39:28.814756+00	60	HUL -> VIM BAR	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
263	2019-01-09 10:39:45.719041+00	59	P&G -> Whisper	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
264	2019-01-09 10:40:35.534476+00	85	Pepsico	1	[{"added": {}}]	51	11
265	2019-01-09 10:44:50.761572+00	86	Cocacola	1	[{"added": {}}]	51	11
266	2019-01-09 10:45:18.773345+00	87	FERRERO	1	[{"added": {}}]	51	11
267	2019-01-09 10:51:23.74301+00	85	Pepsico	2	[{"changed": {"fields": ["brand_logo"]}}]	51	11
268	2019-01-09 10:53:05.002127+00	88	Cocacola -> LIMCA	1	[{"added": {}}]	51	11
269	2019-01-09 10:53:34.116958+00	12	9582288240	1	[{"added": {}}]	14	2
270	2019-01-09 10:54:35.416504+00	5	GST-28	1	[{"added": {}}]	31	11
271	2019-01-09 10:54:52.862407+00	6	CESS - 12	1	[{"added": {}}]	31	11
272	2019-01-09 10:58:05.216356+00	89	Cocacola -> SPRITE	1	[{"added": {}}]	51	11
273	2019-01-09 10:58:27.62191+00	90	COCACOLA	1	[{"added": {}}]	51	11
274	2019-01-09 10:58:41.03366+00	90	COKE	2	[{"changed": {"fields": ["brand_name"]}}]	51	11
275	2019-01-09 10:58:51.133585+00	90	COKE	2	[{"changed": {"fields": ["brand_slug"]}}]	51	11
276	2019-01-09 10:59:06.700831+00	91	FANTA	1	[{"added": {}}]	51	11
277	2019-01-09 10:59:28.224595+00	92	THUMS UP	1	[{"added": {}}]	51	11
278	2019-01-09 10:59:36.560544+00	7	GFDN-Noida - Gram Factory	1	[{"added": {}}, {"added": {"object": "09AAQCA9570J1ZW - https://gramfactorymedia.s3.amazonaws.com/media/shop_photos/shop_name/documents/NOIDA_AEOP_1.pdf", "name": "shop document"}}, {"added": {"object": "18C, Knowledge Park 3, Greator Noida,", "name": "address"}}, {"added": {"object": "18C, Knowledge Park 3, Greator Noida,", "name": "address"}}]	44	2
279	2019-01-09 11:00:11.790578+00	93	FERRERO -> KINDER JOY	1	[{"added": {}}]	51	11
280	2019-01-09 11:00:43.661637+00	94	FERRERO -> TIC TAC	1	[{"added": {}}]	51	11
281	2019-01-09 11:01:03.886692+00	95	MOUNTAIN DEW	1	[{"added": {}}]	51	11
282	2019-01-09 11:01:53.680635+00	96	MIRINDA	1	[{"added": {}}]	51	11
283	2019-01-09 11:04:03.439647+00	96	Pepsico -> MIRINDA	2	[{"changed": {"fields": ["brand_parent"]}}]	51	11
284	2019-01-09 11:04:30.876002+00	97	Pepsico -> PEPSI	1	[{"added": {}}]	51	11
285	2019-01-09 11:05:31.025498+00	98	Pepsico -> PEPSI BLACK	1	[{"added": {}}]	51	11
286	2019-01-09 11:10:45.614123+00	389	Tide Laundary Powder Jasmine & Rose 110gm(MRP-10) Pack-12	3		36	2
287	2019-01-09 11:15:33.038458+00	99	Dabur -> REAL JUICE	1	[{"added": {}}]	51	11
288	2019-01-09 11:16:47.418581+00	100	TAAZA TEA	1	[{"added": {}}]	51	11
289	2019-01-09 11:17:50.630612+00	101	HUL -> BRU COFFEE	1	[{"added": {}}]	51	11
290	2019-01-09 11:18:22.004458+00	102	Nestle -> KIT KAT	1	[{"added": {}}]	51	11
291	2019-01-09 11:18:43.243382+00	103	Nestle -> MUNCH	1	[{"added": {}}]	51	11
292	2019-01-09 11:19:10.522572+00	104	Nestle -> NESCAFE	1	[{"added": {}}]	51	11
293	2019-01-09 11:36:14.615049+00	105	HUL -> RED LABEL	1	[{"added": {}}]	51	11
294	2019-01-09 11:36:46.772824+00	106	Cocacola -> MAAZA	1	[{"added": {}}]	51	11
295	2019-01-09 11:37:08.378181+00	107	Pepsico -> SLICE	1	[{"added": {}}]	51	11
296	2019-01-09 12:01:57.713517+00	36	BEVERAGES	1	[{"added": {}}]	18	11
297	2019-01-09 12:02:05.655589+00	36	BEVERAGES	2	[]	18	11
298	2019-01-09 12:02:08.89354+00	36	BEVERAGES	2	[]	18	11
299	2019-01-09 12:02:39.015841+00	37	BEVERAGES -> Soft Drink	1	[{"added": {}}]	18	11
300	2019-01-09 12:03:13.361288+00	38	BEVERAGES -> Juices	1	[{"added": {}}]	18	11
301	2019-01-09 12:03:32.494827+00	39	BEVERAGES -> Tea	1	[{"added": {}}]	18	11
302	2019-01-09 12:03:47.463844+00	40	BEVERAGES -> Coffee	1	[{"added": {}}]	18	11
303	2019-01-09 12:04:07.647476+00	41	Confectionery	1	[{"added": {}}]	18	11
304	2019-01-09 12:04:19.148252+00	42	Confectionery -> Chocolate	1	[{"added": {}}]	18	11
305	2019-01-09 12:04:38.570065+00	43	Confectionery -> Candy	1	[{"added": {}}]	18	11
306	2019-01-09 12:04:59.162351+00	36	Beverages	2	[{"changed": {"fields": ["category_name"]}}]	18	11
307	2019-01-09 12:09:30.631296+00	9	habxha34_6-i - Retailer	1	[{"added": {}}]	44	7
308	2019-01-09 12:09:41.439587+00	9	habxha34_6-i - Retailer	3		44	7
309	2019-01-09 12:13:51.723194+00	108	Adani Wilmar	1	[{"added": {}}]	51	2
310	2019-01-09 12:14:28.075857+00	109	Adani Wilmar -> Fortune	1	[{"added": {}}]	51	2
311	2019-01-09 12:15:03.002186+00	110	Adani Wilmar -> Raag Gold	1	[{"added": {}}]	51	2
312	2019-01-09 12:15:48.859422+00	111	Amul	1	[{"added": {}}]	51	2
313	2019-01-09 12:17:00.732246+00	112	ITC -> Aashirvaad	1	[{"added": {}}]	51	2
314	2019-01-09 12:17:45.948038+00	113	Marico -> Saffola Oil	1	[{"added": {}}]	51	2
315	2019-01-09 12:17:49.471331+00	2	ADT/PO/07/00002	1	[{"added": {}}, {"added": {"object": "Haldiram Bikaneri bhujia mrp10", "name": "Select Product"}}, {"added": {"object": "Haldiram aloo bhuji mrp5", "name": "Select Product"}}]	65	7
316	2019-01-09 12:18:07.786076+00	2	ADT/PO/07/00002	2	[]	65	7
317	2019-01-09 12:20:20.573408+00	114	Ruchi Soya Ltd	1	[{"added": {}}]	51	2
318	2019-01-09 12:20:51.013139+00	115	Ruchi Soya Ltd -> Mahakosh	1	[{"added": {}}]	51	2
319	2019-01-09 12:22:54.849538+00	116	Ruchi Soya Ltd -> Ruchi Gold	1	[{"added": {}}]	51	2
320	2019-01-09 12:23:50.60814+00	117	Madhusudan	1	[{"added": {}}]	51	2
321	2019-01-09 12:24:18.134163+00	118	Uttam Sugar	1	[{"added": {}}]	51	2
322	2019-01-09 12:25:00.46529+00	5	HUL	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
323	2019-01-09 12:25:49.154772+00	31	Reckitt Benckiser -> Lizol	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
324	2019-01-09 12:26:06.805042+00	6	Marico	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
325	2019-01-09 12:26:17.975303+00	27	Marico -> Nihar	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
326	2019-01-09 12:26:30.119166+00	12	Dabur -> Odonil	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
327	2019-01-09 12:27:41.477969+00	28	Marico -> Parachute	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
328	2019-01-09 12:28:22.453525+00	119	Pepsico -> Tropicana	1	[{"added": {}}]	51	11
329	2019-01-09 12:30:05.185951+00	28	Marico -> Parachute	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
330	2019-01-09 12:34:57.155647+00	28	Marico -> Parachute	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
331	2019-01-09 12:45:01.646762+00	105	HUL -> RED LABEL	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
332	2019-01-09 12:45:14.472293+00	40	ITC -> Sunfeast	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
333	2019-01-09 12:45:26.704727+00	83	ITC -> Vivel	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
334	2019-01-09 13:11:30.354496+00	8	store 3 - Retailer	2	[{"changed": {"fields": ["status"]}}]	44	7
335	2019-01-09 13:11:32.599777+00	5	store 3(Retailer - gm) --mapped to-- Gramfactory-Noida(Gram Factory - gm)(Active)	1	[{"added": {}}]	46	7
336	2019-01-10 04:58:34.770882+00	67	Dabur -> Lal Dant Manjan	2	[{"changed": {"fields": ["brand_logo"]}}]	51	2
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	group
3	auth	permission
4	contenttypes	contenttype
5	sessions	session
6	authtoken	token
7	sites	site
8	allauth	socialtoken
9	allauth	socialapp
10	allauth	socialaccount
11	account	emailaddress
12	account	emailconfirmation
13	accounts	userdocument
14	accounts	user
15	otp	phoneotp
16	categories	categoryposation
17	categories	categorydata
18	categories	category
19	addresses	invoicecitymapping
20	addresses	city
21	addresses	state
22	addresses	country
23	addresses	address
24	addresses	area
25	products	productcategoryhistory
26	products	fragrance
27	products	productvendormapping
28	products	productimage
29	products	productprice
30	products	weight
31	products	tax
32	products	productoption
33	products	productskugenerator
34	products	producthistory
35	products	productcsv
36	products	product
37	products	color
38	products	packagesize
39	products	flavor
40	products	productcategory
41	products	producttaxmapping
42	products	size
43	products	productpricecsv
44	shops	shop
45	shops	shopdocument
46	shops	parentretailermapping
47	shops	shoptype
48	shops	shopphoto
49	shops	retailertype
50	brand	brandposition
51	brand	brand
52	brand	vendor
53	brand	branddata
54	banner	page
55	banner	bannerposition
56	banner	banner
57	banner	bannerslot
58	banner	bannerdata
59	gram_to_brand	orderitem
60	gram_to_brand	grnorderproductmapping
61	gram_to_brand	po_message
62	gram_to_brand	orderhistory
63	gram_to_brand	picklistitems
64	gram_to_brand	orderedproductreserved
65	gram_to_brand	cart
66	gram_to_brand	cartproductmapping
67	gram_to_brand	grnorderproducthistory
68	gram_to_brand	order
69	gram_to_brand	grnorder
70	gram_to_brand	picklist
71	gram_to_brand	brandnote
72	sp_to_gram	orderedproduct
73	sp_to_gram	orderedproductreserved
74	sp_to_gram	spnote
75	sp_to_gram	cartproductmapping
76	sp_to_gram	cart
77	sp_to_gram	order
78	sp_to_gram	orderedproductmapping
79	retailer_to_sp	orderedproductmapping
80	retailer_to_sp	payment
81	retailer_to_sp	customercare
82	retailer_to_sp	note
83	retailer_to_sp	order
84	retailer_to_sp	cart
85	retailer_to_sp	cartproductmapping
86	retailer_to_sp	orderedproduct
87	retailer_to_gram	cart
88	retailer_to_gram	customercare
89	retailer_to_gram	orderedproductmapping
90	retailer_to_gram	payment
91	retailer_to_gram	note
92	retailer_to_gram	orderedproduct
93	retailer_to_gram	order
94	retailer_to_gram	cartproductmapping
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2019-01-07 12:27:59.914774+00
2	contenttypes	0002_remove_content_type_name	2019-01-07 12:27:59.942145+00
3	auth	0001_initial	2019-01-07 12:28:00.044966+00
4	auth	0002_alter_permission_name_max_length	2019-01-07 12:28:00.060954+00
5	auth	0003_alter_user_email_max_length	2019-01-07 12:28:00.072585+00
6	auth	0004_alter_user_username_opts	2019-01-07 12:28:00.083981+00
7	auth	0005_alter_user_last_login_null	2019-01-07 12:28:00.095396+00
8	auth	0006_require_contenttypes_0002	2019-01-07 12:28:00.100436+00
9	auth	0007_alter_validators_add_error_messages	2019-01-07 12:28:00.112021+00
10	auth	0008_alter_user_username_max_length	2019-01-07 12:28:00.123297+00
11	auth	0009_alter_user_last_name_max_length	2019-01-07 12:28:00.136091+00
12	accounts	0001_initial	2019-01-07 12:28:00.220044+00
13	shops	0001_initial	2019-01-07 12:28:00.405093+00
14	addresses	0001_initial	2019-01-07 12:28:00.566531+00
15	admin	0001_initial	2019-01-07 12:28:00.66682+00
16	admin	0002_logentry_remove_auto_add	2019-01-07 12:28:00.682948+00
17	admin	0003_logentry_add_action_flag_choices	2019-01-07 12:28:00.698749+00
18	sites	0001_initial	2019-01-07 12:28:00.712989+00
19	sites	0002_alter_domain_unique	2019-01-07 12:28:00.729586+00
20	allauth	0001_initial	2019-01-07 12:28:00.860205+00
21	authtoken	0001_initial	2019-01-07 12:28:00.895672+00
22	authtoken	0002_auto_20160226_1747	2019-01-07 12:28:00.957289+00
23	banner	0001_initial	2019-01-07 12:28:01.073751+00
24	brand	0001_initial	2019-01-07 12:28:01.189142+00
25	categories	0001_initial	2019-01-07 12:28:01.286076+00
26	products	0001_initial	2019-01-07 12:28:02.169213+00
27	retailer_to_gram	0001_initial	2019-01-07 12:28:02.909248+00
28	gram_to_brand	0001_initial	2019-01-07 12:28:05.469605+00
29	otp	0001_initial	2019-01-07 12:28:05.487777+00
30	retailer_to_sp	0001_initial	2019-01-07 12:28:06.549766+00
31	sessions	0001_initial	2019-01-07 12:28:06.576398+00
32	sp_to_gram	0001_initial	2019-01-07 12:28:07.45358+00
33	products	0002_auto_20190107_2200	2019-01-07 16:31:07.604154+00
34	sp_to_gram	0002_remove_orderedproductreserved_reserve_status	2019-01-07 16:31:07.659684+00
35	account	0001_initial	2019-01-08 06:39:17.473357+00
36	products	0003_auto_20190108_1344	2019-01-08 08:14:29.848643+00
37	gram_to_brand	0002_auto_20190109_0949	2019-01-09 04:19:31.77697+00
38	products	0004_auto_20190109_0949	2019-01-09 04:19:31.880208+00
39	sp_to_gram	0003_orderedproductreserved_reserve_status	2019-01-09 04:19:31.935845+00
40	addresses	0002_auto_20190109_1731	2019-01-09 12:02:12.625118+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
230phqlepx12idz5cnau6sw7jvferj24	NjhkMjE1YTI2NWVkNzlmMmVjNjFjNjI5NWZmNmVmNDM0OTM2NzczZjp7Il9hdXRoX3VzZXJfaGFzaCI6ImY5MTE4ODljYzRkNzA2NjhhZjM3ODZiM2RmN2IzYzg2ZTFlNDY1OTQiLCJfYXV0aF91c2VyX2lkIjoiMiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-21 16:47:28.60737+00
tfgg4sfi04kbmyks1fa6jvpffc0mqmvh	NjhkMjE1YTI2NWVkNzlmMmVjNjFjNjI5NWZmNmVmNDM0OTM2NzczZjp7Il9hdXRoX3VzZXJfaGFzaCI6ImY5MTE4ODljYzRkNzA2NjhhZjM3ODZiM2RmN2IzYzg2ZTFlNDY1OTQiLCJfYXV0aF91c2VyX2lkIjoiMiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-22 04:04:15.969097+00
gpnyh6pknst5q6k2g7t3yg9za67xho79	NjhkMjE1YTI2NWVkNzlmMmVjNjFjNjI5NWZmNmVmNDM0OTM2NzczZjp7Il9hdXRoX3VzZXJfaGFzaCI6ImY5MTE4ODljYzRkNzA2NjhhZjM3ODZiM2RmN2IzYzg2ZTFlNDY1OTQiLCJfYXV0aF91c2VyX2lkIjoiMiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-22 05:35:32.321527+00
1ff9d000pp0y3w5fczhd0w9s9ljuycvd	ZDJlZWEzYmY2NTFiMzM4ZDNhNGNkNzAwNDgzZGU5Y2Y0ZWI2NjUwNTp7Il9hdXRoX3VzZXJfaGFzaCI6IjU4Mzk4NzQ2MWQxMjE5NzVjZTdiMTBkZjc3ZmE4MDk1OTE5OGQ3MGYiLCJfYXV0aF91c2VyX2lkIjoiMSIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-22 06:33:46.954442+00
3g7besxeb7wssm6nvtxpddft8gv03cvj	OGQyNmIxODZiYzQ5MWYwODRjOGZhNjA5OTZhNDA5ZmM2MjFhYmIwNjp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9pZCI6IjEiLCJfYXV0aF91c2VyX2hhc2giOiI1ODM5ODc0NjFkMTIxOTc1Y2U3YjEwZGY3N2ZhODA5NTkxOThkNzBmIn0=	2019-01-22 06:42:29.200269+00
fx6kma2yywv5dgjugmewjhkcyqgdn1ki	MTA4ZTI5OGI0ZmQ0MzQ1MWNlMzM2MTExYmRiYjNmNzRmNjdmZTFmNzp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiNTgzOTg3NDYxZDEyMTk3NWNlN2IxMGRmNzdmYTgwOTU5MTk4ZDcwZiIsIl9hdXRoX3VzZXJfaWQiOiIxIn0=	2019-01-22 07:52:43.309664+00
0u3segd2m5epb4tm1a3o2tk2fbqribdu	ZTk3MGMzYWJmZWZkMDc3NWZlN2FmZmQ1MTFkMThlYTM4MTQ2YmY3NTp7Il9hdXRoX3VzZXJfaWQiOiIxIiwiX2F1dGhfdXNlcl9oYXNoIjoiNTgzOTg3NDYxZDEyMTk3NWNlN2IxMGRmNzdmYTgwOTU5MTk4ZDcwZiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-22 12:15:43.277562+00
0unb25q6x8j4lady9kitffr0nycctau2	NWM0ZDI4MWY5ZTI4MTBjMzg3YWQxMGIwYWIyZWQwNzkyNzhkNzVlNzp7Il9hdXRoX3VzZXJfaWQiOiI1IiwiX2F1dGhfdXNlcl9oYXNoIjoiM2RhN2ExYzBiOWFmNWZkNTAwYjJkZTk2OWEzNWFiMDljYmYzMDFiOSIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiYWNjb3VudF92ZXJpZmllZF9lbWFpbCI6bnVsbH0=	2019-01-22 12:18:22.453908+00
713mcu4uvjyzq0gvwei8902tze3xy9se	ZTk3MGMzYWJmZWZkMDc3NWZlN2FmZmQ1MTFkMThlYTM4MTQ2YmY3NTp7Il9hdXRoX3VzZXJfaWQiOiIxIiwiX2F1dGhfdXNlcl9oYXNoIjoiNTgzOTg3NDYxZDEyMTk3NWNlN2IxMGRmNzdmYTgwOTU5MTk4ZDcwZiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-22 12:28:56.49393+00
q3szxujc0lpyza2vfmyg6qn1j6113q27	ZTg1YjhhMzMxNjkzZDkwNTlkNmU2MDNkYzFlODJlN2M0NWQ4MmRjMjp7Il9hdXRoX3VzZXJfaWQiOiI2IiwiX2F1dGhfdXNlcl9oYXNoIjoiMjgwNjk2YWU4NWI2OWRmOGEwOTVmYzU3MDViNjY1MjQyYjgwZDI2NSIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiYWNjb3VudF92ZXJpZmllZF9lbWFpbCI6bnVsbH0=	2019-01-22 12:36:52.641878+00
w0jmn4rni23daxip3f6c3fe1h5k7qr20	ZTk3MGMzYWJmZWZkMDc3NWZlN2FmZmQ1MTFkMThlYTM4MTQ2YmY3NTp7Il9hdXRoX3VzZXJfaWQiOiIxIiwiX2F1dGhfdXNlcl9oYXNoIjoiNTgzOTg3NDYxZDEyMTk3NWNlN2IxMGRmNzdmYTgwOTU5MTk4ZDcwZiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-22 12:38:22.024802+00
nyxab84d6efb2efcv82kxfx7mzpkzf4y	NjhkMjE1YTI2NWVkNzlmMmVjNjFjNjI5NWZmNmVmNDM0OTM2NzczZjp7Il9hdXRoX3VzZXJfaGFzaCI6ImY5MTE4ODljYzRkNzA2NjhhZjM3ODZiM2RmN2IzYzg2ZTFlNDY1OTQiLCJfYXV0aF91c2VyX2lkIjoiMiIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIn0=	2019-01-23 04:22:29.653243+00
cynjc06veylbpmkgm4y8r56fmu4md29d	ZDIzNDVlNjExNTgxNDIxMTkzMzYxNWM4ODczODc3OTVjNWZlMGJhZTp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiZTM2ODRjMTk0ZjRkNDcwYzQyNWNmZTM1NGY5NDA1Y2U2ZjRiNTA0YyIsImFjY291bnRfdmVyaWZpZWRfZW1haWwiOm51bGwsIl9hdXRoX3VzZXJfaWQiOiI4In0=	2019-01-23 06:21:00.531731+00
3qq0xb5wsicxhldxsrsxtfzgly0gp8e7	NmRlNDYxNDdkMGI2ZWI3ZmYzZDZhNGNkNWE4YmMzN2RiNWY3Njk0NDp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiZTM2ODRjMTk0ZjRkNDcwYzQyNWNmZTM1NGY5NDA1Y2U2ZjRiNTA0YyIsIl9hdXRoX3VzZXJfaWQiOiI4In0=	2019-01-23 06:54:31.772732+00
wxeh6cjg487o57ip0rhfcdxb33myqvjo	MDBmYzMwMDJmMDUzMTI4MWJiOTI1ZTM0MGY5MzEyNzllNjhjNGRlOTp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiYjRkODlmYzYxODJmOWM5NzZmZGEwNmM2ZTJmODE4Y2Q2YzZjNzZjNyIsIl9hdXRoX3VzZXJfaWQiOiI3In0=	2019-01-23 07:07:53.255898+00
56icqk0sbhqr6p0yqnbh3spc7jfpe2k1	MDBmYzMwMDJmMDUzMTI4MWJiOTI1ZTM0MGY5MzEyNzllNjhjNGRlOTp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiYjRkODlmYzYxODJmOWM5NzZmZGEwNmM2ZTJmODE4Y2Q2YzZjNzZjNyIsIl9hdXRoX3VzZXJfaWQiOiI3In0=	2019-01-23 07:09:27.053272+00
x4ci8i1rtljnokh5qsstotm3a0cl3xl5	YjgwOTVjOTRhZWJmNmYzZWU0OTJhNTBhMmI0ZmMyZGM4YmMwY2I5ODp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiNGRhM2FmOThlM2Y4Y2YwZDNlOTNhZGVhYzI1ZTk3ZGViMDgzZGJhNCIsImFjY291bnRfdmVyaWZpZWRfZW1haWwiOm51bGwsIl9hdXRoX3VzZXJfaWQiOiI5In0=	2019-01-23 07:09:37.023343+00
24nqbshfklaroao1m4rkhhkkg9ubzslz	MTA4ZTI5OGI0ZmQ0MzQ1MWNlMzM2MTExYmRiYjNmNzRmNjdmZTFmNzp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiNTgzOTg3NDYxZDEyMTk3NWNlN2IxMGRmNzdmYTgwOTU5MTk4ZDcwZiIsIl9hdXRoX3VzZXJfaWQiOiIxIn0=	2019-01-23 07:25:25.103542+00
tl04j49m8yvzph3qqeirsayfco33er1p	OGYwMjRmNWZhNmIwOGRiNjFiMmQ5NTI0NWVmMzRmZmM4MjAyZDgyYzp7ImFjY291bnRfdmVyaWZpZWRfZW1haWwiOm51bGwsIl9hdXRoX3VzZXJfaWQiOiIxMCIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9oYXNoIjoiMDQzOGFlZTY1NjMwZTYwN2E4N2IzZjlhOWQ3MmZhYTBmYTRlNjY1YSJ9	2019-01-23 08:00:52.596152+00
qw0tgcpteum7ie97jcyoiwujhcaotipn	MzdkMGVhMTZjOTNlYmRlNDRlMDAyYzA5NDgyMjYzNjBmNGUxM2Y5Yjp7Il9hdXRoX3VzZXJfaWQiOiIxMSIsIl9hdXRoX3VzZXJfaGFzaCI6Ijc5NWU4YzA5NzZkMTlmYTFiNjZjMzEzMmYxMjQwOGFmYzcyZDVmZjIiLCJfYXV0aF91c2VyX2JhY2tlbmQiOiJkamFuZ28uY29udHJpYi5hdXRoLmJhY2tlbmRzLk1vZGVsQmFja2VuZCJ9	2019-01-23 09:51:51.552662+00
h2jfkxnykjh9lqohfyib0ehw14roh8ls	Njc1YzQ4YTIxMDc4N2ZjNDEwN2IwMTA3MThjMWNiMjhkMTQzMTkwODp7Il9hdXRoX3VzZXJfaGFzaCI6ImUzNjg0YzE5NGY0ZDQ3MGM0MjVjZmUzNTRmOTQwNWNlNmY0YjUwNGMiLCJfYXV0aF91c2VyX2JhY2tlbmQiOiJkamFuZ28uY29udHJpYi5hdXRoLmJhY2tlbmRzLk1vZGVsQmFja2VuZCIsIl9hdXRoX3VzZXJfaWQiOiI4In0=	2019-01-23 10:45:16.218324+00
pphv96pntui3jhplquzios5kiqu2k2oz	Njc1YzQ4YTIxMDc4N2ZjNDEwN2IwMTA3MThjMWNiMjhkMTQzMTkwODp7Il9hdXRoX3VzZXJfaGFzaCI6ImUzNjg0YzE5NGY0ZDQ3MGM0MjVjZmUzNTRmOTQwNWNlNmY0YjUwNGMiLCJfYXV0aF91c2VyX2JhY2tlbmQiOiJkamFuZ28uY29udHJpYi5hdXRoLmJhY2tlbmRzLk1vZGVsQmFja2VuZCIsIl9hdXRoX3VzZXJfaWQiOiI4In0=	2019-01-23 11:41:52.632418+00
v9lrq0h122chkwofzrbumdsd5igh152y	ZjQ1NTg5ZDIzNDRlNWRmMjAzNzdlYjUzMzU0NWVlMjNmMDJjNzM3Njp7ImFjY291bnRfdmVyaWZpZWRfZW1haWwiOm51bGwsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9pZCI6IjEzIiwiX2F1dGhfdXNlcl9oYXNoIjoiNWZmMjJhMDdjNDZjNTYyYWFiOThkMzEyZWQ4MTVhMmQ5YmJhYjA3ZSJ9	2019-01-23 11:55:10.782114+00
1xanfcl84by6dmi3i9ewfvbeq803vlsh	NGZkYTkzOTVkMzI5MmFmM2EwNmEyZmUxZjIxMTNlMGRmNzBlZWMxZjp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9pZCI6IjciLCJfYXV0aF91c2VyX2hhc2giOiJiNGQ4OWZjNjE4MmY5Yzk3NmZkYTA2YzZlMmY4MThjZDZjNmM3NmM3In0=	2019-01-24 05:37:00.833844+00
d8osrihvflsyus8gsz7uvmzt7pu0uzoa	NGZkYTkzOTVkMzI5MmFmM2EwNmEyZmUxZjIxMTNlMGRmNzBlZWMxZjp7Il9hdXRoX3VzZXJfYmFja2VuZCI6ImRqYW5nby5jb250cmliLmF1dGguYmFja2VuZHMuTW9kZWxCYWNrZW5kIiwiX2F1dGhfdXNlcl9pZCI6IjciLCJfYXV0aF91c2VyX2hhc2giOiJiNGQ4OWZjNjE4MmY5Yzk3NmZkYTA2YzZlMmY4MThjZDZjNmM3NmM3In0=	2019-01-24 08:07:54.547595+00
\.


--
-- Data for Name: django_site; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.django_site (id, domain, name) FROM stdin;
1	example.com	example.com
\.


--
-- Data for Name: gram_to_brand_brandnote; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_brandnote (id, brand_note_id, note_type, amount, created_at, modified_at, grn_order_id, last_modified_by_id, order_id) FROM stdin;
\.


--
-- Data for Name: gram_to_brand_cart; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_cart (id, po_no, po_status, po_creation_date, po_validity_date, payment_term, delivery_term, po_amount, cart_product_mapping_csv, is_approve, created_at, modified_at, brand_id, gf_billing_address_id, gf_shipping_address_id, last_modified_by_id, po_message_id, po_raised_by_id, shop_id, supplier_name_id, supplier_state_id) FROM stdin;
1	ADT/PO/07/00001	\N	2019-01-08	2019-01-16			0		t	2019-01-08 12:11:05.572058+00	2019-01-08 12:11:21.145591+00	8	2	1	\N	\N	\N	\N	1	1
2	ADT/PO/07/00002	finance_approved	2019-01-09	2019-01-26			0		t	2019-01-09 12:17:49.446293+00	2019-01-09 12:18:07.788043+00	51	11	1	7	\N	7	\N	2	2
\.


--
-- Data for Name: gram_to_brand_cartproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_cartproductmapping (id, inner_case_size, case_size, number_of_cases, qty, scheme, price, total_price, cart_id, cart_product_id) FROM stdin;
1	2	8	1	16	0	20	320	1	28
2	6	48	2	576	0	20	11520	1	29
3	3	24	3	216	0	20	4320	1	31
4	10	300	3	9000	0	200	1800000	2	351
5	12	504	2	12096	0	250	3024000	2	342
\.


--
-- Data for Name: gram_to_brand_grnorder; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_grnorder (id, invoice_no, grn_id, grn_date, created_at, modified_at, last_modified_by_id, order_id, order_item_id) FROM stdin;
1	kjkdjsadlkj	18-19/1	2019-01-08	2019-01-08 12:13:06.489064+00	2019-01-08 12:13:06.491022+00	\N	1	\N
2	43443	18-19/2	2019-01-08	2019-01-08 12:47:56.617122+00	2019-01-08 12:47:56.618708+00	\N	1	\N
3	SP/INVOICE/6	18-19/3	2019-01-09	2019-01-09 06:20:28.022252+00	2019-01-09 06:20:28.023983+00	\N	1	\N
4	786	18-19/4	2019-01-09	2019-01-09 06:40:32.220695+00	2019-01-09 06:40:32.222348+00	\N	1	\N
\.


--
-- Data for Name: gram_to_brand_grnorderproducthistory; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_grnorderproducthistory (id, invoice_no, grn_id, changed_price, manufacture_date, expiry_date, available_qty, ordered_qty, delivered_qty, returned_qty, damaged_qty, created_at, modified_at, grn_order_id, last_modified_by_id, order_id, order_item_id, product_id) FROM stdin;
\.


--
-- Data for Name: gram_to_brand_grnorderproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_grnorderproductmapping (id, po_product_quantity, po_product_price, already_grned_product, product_invoice_price, product_invoice_qty, manufacture_date, expiry_date, available_qty, ordered_qty, delivered_qty, returned_qty, damaged_qty, created_at, modified_at, grn_order_id, last_modified_by_id, product_id) FROM stdin;
1	16	20	0	0	1	2019-01-01	2019-01-17	0	1	1	0	0	2019-01-08 12:13:06.492976+00	2019-01-09 09:24:40.272019+00	1	\N	28
4	16	20	1	0	5	2019-01-01	2019-01-14	0	1	5	0	0	2019-01-08 12:47:56.62061+00	2019-01-09 09:24:40.286408+00	2	\N	28
7	16	20	6	-1	3	2019-01-01	2019-01-09	0	1	3	0	0	2019-01-09 06:20:28.025949+00	2019-01-09 09:24:40.300717+00	3	\N	28
10	16	20	9	0	7	2019-01-01	2019-01-09	0	1	7	0	0	2019-01-09 06:40:32.224362+00	2019-01-09 09:24:40.316772+00	4	\N	28
3	216	20	0	0	3	2019-01-01	2019-01-17	0	4	3	0	0	2019-01-08 12:13:06.496121+00	2019-01-09 13:17:43.360479+00	1	\N	31
6	216	20	3	0	5	2019-01-02	2019-01-09	0	4	5	0	0	2019-01-08 12:47:56.623609+00	2019-01-09 13:17:43.376261+00	2	\N	31
8	216	20	8	0	3	2019-01-01	2019-01-09	0	4	3	0	0	2019-01-09 06:20:28.027635+00	2019-01-09 13:17:43.39031+00	3	\N	31
12	216	20	11	0	100	2019-01-01	2019-01-09	0	4	100	0	0	2019-01-09 06:40:32.227359+00	2019-01-09 13:17:43.404775+00	4	\N	31
2	576	20	0	0	2	2019-01-01	2019-01-17	0	1	2	0	0	2019-01-08 12:13:06.494735+00	2019-01-09 13:18:09.079786+00	1	\N	29
5	576	20	2	0	5	2019-01-01	2019-01-14	0	1	5	0	0	2019-01-08 12:47:56.622238+00	2019-01-09 13:18:09.096088+00	2	\N	29
11	576	20	10	0	100	2019-01-01	2019-01-09	0	1	100	0	0	2019-01-09 06:40:32.225961+00	2019-01-09 13:18:09.111223+00	4	\N	29
9	576	20	7	0	3	2019-01-01	2019-01-09	0	1	3	0	0	2019-01-09 06:20:28.02906+00	2019-01-09 13:18:09.125994+00	3	\N	29
\.


--
-- Data for Name: gram_to_brand_order; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_order (id, order_no, total_mrp, total_discount_amount, total_tax_amount, total_final_amount, order_status, created_at, modified_at, billing_address_id, last_modified_by_id, ordered_by_id, ordered_cart_id, received_by_id, shipping_address_id, shop_id) FROM stdin;
1	ADT/PO/07/00001	0	0	0	16160	partially_delivered	2019-01-08 12:11:05.581909+00	2019-01-09 06:40:32.273565+00	2	\N	\N	1	\N	1	\N
2	ADT/PO/07/00002	0	0	0	4824000	finance_approved	2019-01-09 12:17:49.456643+00	2019-01-09 12:18:07.794241+00	11	\N	\N	2	\N	1	\N
\.


--
-- Data for Name: gram_to_brand_orderedproductreserved; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_orderedproductreserved (id, reserved_qty, order_reserve_end_time, created_at, modified_at, reserve_status, cart_id, order_product_reserved_id, product_id) FROM stdin;
9	1	2019-01-08 12:57:06.955443+00	2019-01-08 12:48:22.211226+00	2019-01-08 12:49:06.955561+00	ordered	1	4	28
8	1	2019-01-08 12:57:06.965421+00	2019-01-08 12:48:22.19629+00	2019-01-08 12:49:06.965538+00	ordered	1	1	28
7	1	2019-01-08 12:57:06.97525+00	2019-01-08 12:48:22.057319+00	2019-01-08 12:49:06.975364+00	ordered	1	5	29
6	1	2019-01-08 12:57:06.984987+00	2019-01-08 12:48:22.042386+00	2019-01-08 12:49:06.985104+00	ordered	1	2	29
5	1	2019-01-08 12:57:06.994777+00	2019-01-08 12:48:21.885691+00	2019-01-08 12:49:06.994896+00	ordered	1	6	31
4	1	2019-01-08 12:57:07.005041+00	2019-01-08 12:48:21.869656+00	2019-01-08 12:49:07.005156+00	ordered	1	3	31
3	1	2019-01-08 12:57:07.014962+00	2019-01-08 12:44:54.4403+00	2019-01-08 12:49:07.01508+00	ordered	1	1	28
2	2	2019-01-08 12:57:07.024501+00	2019-01-08 12:44:54.299038+00	2019-01-08 12:49:07.024617+00	ordered	1	2	29
1	3	2019-01-08 12:57:07.034558+00	2019-01-08 12:44:54.147435+00	2019-01-08 12:49:07.034679+00	ordered	1	3	31
15	1	2019-01-08 12:59:41.937902+00	2019-01-08 12:51:25.054991+00	2019-01-08 12:51:41.938034+00	ordered	2	4	28
14	1	2019-01-08 12:59:41.947575+00	2019-01-08 12:51:25.039552+00	2019-01-08 12:51:41.947703+00	ordered	2	1	28
13	1	2019-01-08 12:59:41.957082+00	2019-01-08 12:51:24.871085+00	2019-01-08 12:51:41.957194+00	ordered	2	5	29
12	1	2019-01-08 12:59:41.966563+00	2019-01-08 12:51:24.84133+00	2019-01-08 12:51:41.966675+00	ordered	2	2	29
11	1	2019-01-08 12:59:41.976958+00	2019-01-08 12:51:24.692372+00	2019-01-08 12:51:41.977116+00	ordered	2	6	31
10	1	2019-01-08 12:59:41.986939+00	2019-01-08 12:51:24.672256+00	2019-01-08 12:51:41.987059+00	ordered	2	3	31
21	1	2019-01-08 13:27:10.518544+00	2019-01-08 13:18:48.677143+00	2019-01-08 13:19:10.518784+00	ordered	3	4	28
20	1	2019-01-08 13:27:10.528841+00	2019-01-08 13:18:48.66197+00	2019-01-08 13:19:10.528963+00	ordered	3	1	28
19	1	2019-01-08 13:27:10.538542+00	2019-01-08 13:18:48.515729+00	2019-01-08 13:19:10.538663+00	ordered	3	5	29
18	1	2019-01-08 13:27:10.548592+00	2019-01-08 13:18:48.500696+00	2019-01-08 13:19:10.548719+00	ordered	3	2	29
17	1	2019-01-08 13:27:10.558856+00	2019-01-08 13:18:48.354129+00	2019-01-08 13:19:10.558976+00	ordered	3	6	31
16	1	2019-01-08 13:27:10.568604+00	2019-01-08 13:18:48.337109+00	2019-01-08 13:19:10.568726+00	ordered	3	3	31
27	1	2019-01-08 14:08:15.467965+00	2019-01-08 14:00:09.313945+00	2019-01-08 14:00:15.468104+00	ordered	4	4	28
26	1	2019-01-08 14:08:15.485874+00	2019-01-08 14:00:09.296803+00	2019-01-08 14:00:15.486074+00	ordered	4	1	28
25	1	2019-01-08 14:08:15.499954+00	2019-01-08 14:00:09.14599+00	2019-01-08 14:00:15.500177+00	ordered	4	5	29
24	1	2019-01-08 14:08:15.510416+00	2019-01-08 14:00:09.130412+00	2019-01-08 14:00:15.510569+00	ordered	4	2	29
23	1	2019-01-08 14:08:15.520721+00	2019-01-08 14:00:08.878017+00	2019-01-08 14:00:15.520839+00	ordered	4	6	31
22	1	2019-01-08 14:08:15.53046+00	2019-01-08 14:00:08.859747+00	2019-01-08 14:00:15.530605+00	ordered	4	3	31
28	1	2019-01-09 06:13:28.041702+00	2019-01-09 06:04:58.177895+00	2019-01-09 06:05:28.041856+00	ordered	5	3	31
29	1	2019-01-09 06:13:28.051222+00	2019-01-09 06:04:58.200064+00	2019-01-09 06:05:28.051329+00	ordered	5	6	31
30	1	2019-01-09 06:13:28.060275+00	2019-01-09 06:04:58.349524+00	2019-01-09 06:05:28.060411+00	ordered	5	2	29
31	1	2019-01-09 06:13:28.075336+00	2019-01-09 06:04:58.366286+00	2019-01-09 06:05:28.075489+00	ordered	5	5	29
32	1	2019-01-09 06:13:28.084691+00	2019-01-09 06:04:58.633409+00	2019-01-09 06:05:28.084814+00	ordered	5	1	28
33	1	2019-01-09 06:13:28.094078+00	2019-01-09 06:04:58.651491+00	2019-01-09 06:05:28.094204+00	ordered	5	4	28
34	1	2019-01-09 06:29:02.413784+00	2019-01-09 06:21:02.414055+00	2019-01-09 06:21:02.414065+00	reserved	6	3	31
35	1	2019-01-09 06:29:02.430068+00	2019-01-09 06:21:02.430279+00	2019-01-09 06:21:02.430289+00	reserved	6	6	31
36	1	2019-01-09 06:29:02.444983+00	2019-01-09 06:21:02.445183+00	2019-01-09 06:21:02.445193+00	reserved	6	8	31
37	1	2019-01-09 06:29:02.565046+00	2019-01-09 06:21:02.565276+00	2019-01-09 06:21:02.565287+00	reserved	6	2	29
38	1	2019-01-09 06:29:02.580625+00	2019-01-09 06:21:02.58083+00	2019-01-09 06:21:02.580841+00	reserved	6	5	29
39	1	2019-01-09 06:29:02.596468+00	2019-01-09 06:21:02.59668+00	2019-01-09 06:21:02.596691+00	reserved	6	9	29
40	3	2019-01-09 06:52:35.864482+00	2019-01-09 06:36:27.308028+00	2019-01-09 06:44:35.864644+00	ordered	7	1	28
41	3	2019-01-09 06:52:35.874517+00	2019-01-09 06:36:27.324918+00	2019-01-09 06:44:35.874633+00	ordered	7	4	28
42	3	2019-01-09 06:52:35.883803+00	2019-01-09 06:36:27.340651+00	2019-01-09 06:44:35.883916+00	ordered	7	7	28
43	2	2019-01-09 06:52:35.893002+00	2019-01-09 06:36:27.485638+00	2019-01-09 06:44:35.893117+00	ordered	7	3	31
44	2	2019-01-09 06:52:35.903274+00	2019-01-09 06:36:27.500784+00	2019-01-09 06:44:35.903392+00	ordered	7	6	31
45	2	2019-01-09 06:52:35.913062+00	2019-01-09 06:36:27.515625+00	2019-01-09 06:44:35.91318+00	ordered	7	8	31
46	2	2019-01-09 06:52:35.92306+00	2019-01-09 06:36:27.656154+00	2019-01-09 06:44:35.923176+00	ordered	7	2	29
47	2	2019-01-09 06:52:35.932397+00	2019-01-09 06:36:27.670813+00	2019-01-09 06:44:35.932514+00	ordered	7	5	29
48	2	2019-01-09 06:52:35.941737+00	2019-01-09 06:36:27.685218+00	2019-01-09 06:44:35.941875+00	ordered	7	9	29
49	5	2019-01-09 06:52:35.952853+00	2019-01-09 06:41:30.276975+00	2019-01-09 06:44:35.952979+00	ordered	7	1	28
50	5	2019-01-09 06:52:35.962753+00	2019-01-09 06:41:30.296787+00	2019-01-09 06:44:35.962879+00	ordered	7	4	28
51	5	2019-01-09 06:52:35.972386+00	2019-01-09 06:41:30.312262+00	2019-01-09 06:44:35.972502+00	ordered	7	7	28
52	5	2019-01-09 06:52:35.982169+00	2019-01-09 06:41:30.326655+00	2019-01-09 06:44:35.982322+00	ordered	7	10	28
53	2	2019-01-09 06:52:35.993132+00	2019-01-09 06:41:30.468417+00	2019-01-09 06:44:35.993263+00	ordered	7	2	29
54	2	2019-01-09 06:52:36.007625+00	2019-01-09 06:41:30.483804+00	2019-01-09 06:44:36.007775+00	ordered	7	5	29
55	2	2019-01-09 06:52:36.017519+00	2019-01-09 06:41:30.49888+00	2019-01-09 06:44:36.017659+00	ordered	7	9	29
56	2	2019-01-09 06:52:36.027317+00	2019-01-09 06:41:30.513754+00	2019-01-09 06:44:36.027454+00	ordered	7	11	29
57	4	2019-01-09 06:52:36.038144+00	2019-01-09 06:41:30.652567+00	2019-01-09 06:44:36.038297+00	ordered	7	3	31
58	4	2019-01-09 06:52:36.04826+00	2019-01-09 06:41:30.667336+00	2019-01-09 06:44:36.048387+00	ordered	7	6	31
59	4	2019-01-09 06:52:36.057872+00	2019-01-09 06:41:30.682016+00	2019-01-09 06:44:36.057988+00	ordered	7	8	31
60	4	2019-01-09 06:52:36.067451+00	2019-01-09 06:41:30.696991+00	2019-01-09 06:44:36.067595+00	ordered	7	12	31
61	1	2019-01-09 08:13:52.258118+00	2019-01-09 08:04:38.719937+00	2019-01-09 08:05:52.258301+00	ordered	8	1	28
62	1	2019-01-09 08:13:52.268122+00	2019-01-09 08:04:38.736607+00	2019-01-09 08:05:52.268282+00	ordered	8	4	28
63	1	2019-01-09 08:13:52.278198+00	2019-01-09 08:04:38.751785+00	2019-01-09 08:05:52.278342+00	ordered	8	7	28
64	1	2019-01-09 08:13:52.288431+00	2019-01-09 08:04:38.766834+00	2019-01-09 08:05:52.288551+00	ordered	8	10	28
65	1	2019-01-09 08:13:52.29783+00	2019-01-09 08:04:38.879187+00	2019-01-09 08:05:52.297963+00	ordered	8	2	29
66	1	2019-01-09 08:13:52.308709+00	2019-01-09 08:04:38.89462+00	2019-01-09 08:05:52.308848+00	ordered	8	5	29
67	1	2019-01-09 08:13:52.318338+00	2019-01-09 08:04:38.909767+00	2019-01-09 08:05:52.318461+00	ordered	8	9	29
68	1	2019-01-09 08:13:52.327888+00	2019-01-09 08:04:38.925118+00	2019-01-09 08:05:52.328013+00	ordered	8	11	29
69	1	2019-01-09 09:32:39.802713+00	2019-01-09 09:24:39.802971+00	2019-01-09 09:24:39.802982+00	reserved	6	3	31
70	1	2019-01-09 09:32:39.823899+00	2019-01-09 09:24:39.824084+00	2019-01-09 09:24:39.824094+00	reserved	6	6	31
71	1	2019-01-09 09:32:39.843344+00	2019-01-09 09:24:39.843529+00	2019-01-09 09:24:39.843539+00	reserved	6	8	31
72	1	2019-01-09 09:32:39.873319+00	2019-01-09 09:24:39.873519+00	2019-01-09 09:24:39.87353+00	reserved	6	12	31
73	1	2019-01-09 09:32:40.091174+00	2019-01-09 09:24:40.091404+00	2019-01-09 09:24:40.091415+00	reserved	6	2	29
74	1	2019-01-09 09:32:40.106143+00	2019-01-09 09:24:40.106328+00	2019-01-09 09:24:40.106338+00	reserved	6	5	29
75	1	2019-01-09 09:32:40.121047+00	2019-01-09 09:24:40.121239+00	2019-01-09 09:24:40.121249+00	reserved	6	9	29
76	1	2019-01-09 09:32:40.135444+00	2019-01-09 09:24:40.135641+00	2019-01-09 09:24:40.135652+00	reserved	6	11	29
77	1	2019-01-09 09:32:40.277524+00	2019-01-09 09:24:40.277743+00	2019-01-09 09:24:40.277755+00	reserved	6	1	28
78	1	2019-01-09 09:32:40.291822+00	2019-01-09 09:24:40.29202+00	2019-01-09 09:24:40.292031+00	reserved	6	4	28
79	1	2019-01-09 09:32:40.306377+00	2019-01-09 09:24:40.306594+00	2019-01-09 09:24:40.306605+00	reserved	6	7	28
80	1	2019-01-09 09:32:40.322406+00	2019-01-09 09:24:40.322599+00	2019-01-09 09:24:40.32261+00	reserved	6	10	28
81	1	2019-01-09 09:32:52.988235+00	2019-01-09 09:24:52.988481+00	2019-01-09 09:24:52.988493+00	reserved	6	3	31
82	1	2019-01-09 09:32:53.00479+00	2019-01-09 09:24:53.005014+00	2019-01-09 09:24:53.005024+00	reserved	6	6	31
83	1	2019-01-09 09:32:53.019599+00	2019-01-09 09:24:53.01978+00	2019-01-09 09:24:53.019791+00	reserved	6	8	31
84	1	2019-01-09 09:32:53.034648+00	2019-01-09 09:24:53.034821+00	2019-01-09 09:24:53.034831+00	reserved	6	12	31
85	1	2019-01-09 09:32:53.181899+00	2019-01-09 09:24:53.18211+00	2019-01-09 09:24:53.182121+00	reserved	6	2	29
86	1	2019-01-09 09:32:53.197765+00	2019-01-09 09:24:53.197972+00	2019-01-09 09:24:53.197983+00	reserved	6	5	29
87	1	2019-01-09 09:32:53.21357+00	2019-01-09 09:24:53.21378+00	2019-01-09 09:24:53.213791+00	reserved	6	11	29
88	1	2019-01-09 09:33:05.918567+00	2019-01-09 09:25:05.918789+00	2019-01-09 09:25:05.9188+00	reserved	6	3	31
89	1	2019-01-09 09:33:05.935203+00	2019-01-09 09:25:05.935418+00	2019-01-09 09:25:05.935428+00	reserved	6	6	31
90	1	2019-01-09 09:33:05.951316+00	2019-01-09 09:25:05.95154+00	2019-01-09 09:25:05.95155+00	reserved	6	8	31
91	1	2019-01-09 09:33:05.969627+00	2019-01-09 09:25:05.969856+00	2019-01-09 09:25:05.969867+00	reserved	6	12	31
92	1	2019-01-09 09:33:06.189231+00	2019-01-09 09:25:06.18946+00	2019-01-09 09:25:06.189471+00	reserved	6	2	29
93	1	2019-01-09 09:33:06.204936+00	2019-01-09 09:25:06.205153+00	2019-01-09 09:25:06.205163+00	reserved	6	5	29
94	1	2019-01-09 09:33:06.220391+00	2019-01-09 09:25:06.220611+00	2019-01-09 09:25:06.220622+00	reserved	6	11	29
95	1	2019-01-09 13:23:32.644099+00	2019-01-09 13:13:47.338541+00	2019-01-09 13:15:32.644239+00	ordered	9	2	29
96	1	2019-01-09 13:23:32.65377+00	2019-01-09 13:13:47.355608+00	2019-01-09 13:15:32.653918+00	ordered	9	5	29
97	1	2019-01-09 13:23:32.663665+00	2019-01-09 13:13:47.370813+00	2019-01-09 13:15:32.663817+00	ordered	9	11	29
98	1	2019-01-09 13:23:32.673465+00	2019-01-09 13:13:52.868696+00	2019-01-09 13:15:32.673649+00	ordered	9	2	29
99	1	2019-01-09 13:23:32.683269+00	2019-01-09 13:13:52.889776+00	2019-01-09 13:15:32.683393+00	ordered	9	5	29
100	1	2019-01-09 13:23:32.693814+00	2019-01-09 13:13:52.90582+00	2019-01-09 13:15:32.693935+00	ordered	9	11	29
101	1	2019-01-09 13:23:32.703289+00	2019-01-09 13:14:48.661984+00	2019-01-09 13:15:32.703403+00	ordered	9	2	29
102	1	2019-01-09 13:23:32.716907+00	2019-01-09 13:14:48.677689+00	2019-01-09 13:15:32.717075+00	ordered	9	5	29
103	1	2019-01-09 13:23:32.726968+00	2019-01-09 13:14:48.692955+00	2019-01-09 13:15:32.727124+00	ordered	9	11	29
104	93	2019-01-09 13:25:43.366127+00	2019-01-09 13:17:43.36633+00	2019-01-09 13:17:43.36634+00	reserved	10	3	31
105	93	2019-01-09 13:25:43.381528+00	2019-01-09 13:17:43.381701+00	2019-01-09 13:17:43.381711+00	reserved	10	6	31
106	93	2019-01-09 13:25:43.395787+00	2019-01-09 13:17:43.39596+00	2019-01-09 13:17:43.39597+00	reserved	10	8	31
107	93	2019-01-09 13:25:43.410297+00	2019-01-09 13:17:43.410471+00	2019-01-09 13:17:43.410481+00	reserved	10	12	31
108	91	2019-01-09 13:26:09.085713+00	2019-01-09 13:18:09.085932+00	2019-01-09 13:18:09.085942+00	reserved	10	2	29
109	91	2019-01-09 13:26:09.101731+00	2019-01-09 13:18:09.101931+00	2019-01-09 13:18:09.101942+00	reserved	10	5	29
110	91	2019-01-09 13:26:09.117037+00	2019-01-09 13:18:09.117228+00	2019-01-09 13:18:09.117238+00	reserved	10	11	29
111	91	2019-01-09 13:26:09.131423+00	2019-01-09 13:18:09.131594+00	2019-01-09 13:18:09.131604+00	reserved	10	9	29
\.


--
-- Data for Name: gram_to_brand_orderhistory; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_orderhistory (id, order_no, total_mrp, total_discount_amount, total_tax_amount, total_final_amount, order_status, created_at, modified_at, billing_address_id, buyer_shop_id, last_modified_by_id, ordered_by_id, ordered_cart_id, received_by_id, seller_shop_id, shipping_address_id) FROM stdin;
\.


--
-- Data for Name: gram_to_brand_orderitem; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_orderitem (id, ordered_qty, ordered_product_status, ordered_price, item_status, total_delivered_qty, total_returned_qty, total_damaged_qty, created_at, modified_at, last_modified_by_id, order_id, ordered_product_id) FROM stdin;
1	8	\N	20	partially_delivered	16	0	0	2019-01-08 12:11:05.585996+00	2019-01-09 06:40:32.237719+00	\N	1	28
2	96	\N	20	partially_delivered	110	0	0	2019-01-08 12:11:05.596616+00	2019-01-09 06:40:32.250765+00	\N	1	29
3	72	\N	20	partially_delivered	111	0	0	2019-01-08 12:11:05.606013+00	2019-01-09 06:40:32.263673+00	\N	1	31
4	900	\N	200		0	0	0	2019-01-09 12:17:49.460239+00	2019-01-09 12:17:49.460254+00	\N	2	351
5	1008	\N	250		0	0	0	2019-01-09 12:17:49.469882+00	2019-01-09 12:17:49.469898+00	\N	2	342
\.


--
-- Data for Name: gram_to_brand_picklist; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_picklist (id, created_at, modified_at, status, cart_id, order_id) FROM stdin;
1	2019-01-08 12:44:54.121395+00	2019-01-08 12:49:06.943743+00	t	1	1
2	2019-01-08 12:51:24.646881+00	2019-01-08 12:51:41.925996+00	t	2	2
3	2019-01-08 13:18:48.311433+00	2019-01-08 13:19:10.496017+00	t	3	3
4	2019-01-08 14:00:08.833408+00	2019-01-08 14:00:15.455791+00	t	4	4
5	2019-01-09 06:04:58.149854+00	2019-01-09 06:05:28.027229+00	t	5	5
7	2019-01-09 06:36:27.282783+00	2019-01-09 06:44:35.851743+00	t	7	6
8	2019-01-09 08:04:38.694389+00	2019-01-09 08:05:52.245652+00	t	8	7
6	2019-01-09 06:18:53.520572+00	2019-01-09 09:25:05.895549+00	f	6	\N
9	2019-01-09 13:13:47.311025+00	2019-01-09 13:15:32.631826+00	t	9	8
10	2019-01-09 13:17:43.341523+00	2019-01-09 13:19:51.58921+00	f	10	\N
\.


--
-- Data for Name: gram_to_brand_picklistitems; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_picklistitems (id, pick_qty, return_qty, damage_qty, created_at, modified_at, grn_order_id, pick_list_id, product_id) FROM stdin;
1	3	0	0	2019-01-08 12:44:54.154168+00	2019-01-08 12:44:54.154185+00	1	1	31
2	2	0	0	2019-01-08 12:44:54.30451+00	2019-01-08 12:44:54.304529+00	1	1	29
3	1	0	0	2019-01-08 12:44:54.446344+00	2019-01-08 12:44:54.446358+00	1	1	28
4	1	0	0	2019-01-08 12:48:21.875954+00	2019-01-08 12:48:21.875968+00	1	1	31
5	1	0	0	2019-01-08 12:48:21.891315+00	2019-01-08 12:48:21.891329+00	2	1	31
6	1	0	0	2019-01-08 12:48:22.048012+00	2019-01-08 12:48:22.048033+00	1	1	29
7	1	0	0	2019-01-08 12:48:22.06292+00	2019-01-08 12:48:22.062937+00	2	1	29
8	1	0	0	2019-01-08 12:48:22.201818+00	2019-01-08 12:48:22.201834+00	1	1	28
9	1	0	0	2019-01-08 12:48:22.216576+00	2019-01-08 12:48:22.216592+00	2	1	28
10	1	0	0	2019-01-08 12:51:24.678319+00	2019-01-08 12:51:24.678333+00	1	2	31
11	1	0	0	2019-01-08 12:51:24.6982+00	2019-01-08 12:51:24.698216+00	2	2	31
12	1	0	0	2019-01-08 12:51:24.861346+00	2019-01-08 12:51:24.861374+00	1	2	29
13	1	0	0	2019-01-08 12:51:24.876669+00	2019-01-08 12:51:24.876685+00	2	2	29
14	1	0	0	2019-01-08 12:51:25.045053+00	2019-01-08 12:51:25.045068+00	1	2	28
15	1	0	0	2019-01-08 12:51:25.060733+00	2019-01-08 12:51:25.060751+00	2	2	28
16	1	0	0	2019-01-08 13:18:48.343971+00	2019-01-08 13:18:48.343988+00	1	3	31
17	1	0	0	2019-01-08 13:18:48.359644+00	2019-01-08 13:18:48.35966+00	2	3	31
18	1	0	0	2019-01-08 13:18:48.506171+00	2019-01-08 13:18:48.506188+00	1	3	29
19	1	0	0	2019-01-08 13:18:48.521089+00	2019-01-08 13:18:48.521104+00	2	3	29
20	1	0	0	2019-01-08 13:18:48.667521+00	2019-01-08 13:18:48.667539+00	1	3	28
21	1	0	0	2019-01-08 13:18:48.682747+00	2019-01-08 13:18:48.682762+00	2	3	28
22	1	0	0	2019-01-08 14:00:08.866104+00	2019-01-08 14:00:08.866121+00	1	4	31
23	1	0	0	2019-01-08 14:00:08.883811+00	2019-01-08 14:00:08.883834+00	2	4	31
24	1	0	0	2019-01-08 14:00:09.136103+00	2019-01-08 14:00:09.136118+00	1	4	29
25	1	0	0	2019-01-08 14:00:09.151902+00	2019-01-08 14:00:09.151928+00	2	4	29
26	1	0	0	2019-01-08 14:00:09.302626+00	2019-01-08 14:00:09.302645+00	1	4	28
27	1	0	0	2019-01-08 14:00:09.319873+00	2019-01-08 14:00:09.319897+00	2	4	28
28	1	0	0	2019-01-09 06:04:58.184179+00	2019-01-09 06:04:58.184194+00	1	5	31
29	1	0	0	2019-01-09 06:04:58.205819+00	2019-01-09 06:04:58.205833+00	2	5	31
30	1	0	0	2019-01-09 06:04:58.35503+00	2019-01-09 06:04:58.355045+00	1	5	29
31	1	0	0	2019-01-09 06:04:58.374612+00	2019-01-09 06:04:58.374631+00	2	5	29
32	1	0	0	2019-01-09 06:04:58.641754+00	2019-01-09 06:04:58.641776+00	1	5	28
33	1	0	0	2019-01-09 06:04:58.657243+00	2019-01-09 06:04:58.657265+00	2	5	28
34	1	0	0	2019-01-09 06:21:02.420348+00	2019-01-09 06:21:02.420364+00	1	6	31
35	1	0	0	2019-01-09 06:21:02.435859+00	2019-01-09 06:21:02.435874+00	2	6	31
36	1	0	0	2019-01-09 06:21:02.450497+00	2019-01-09 06:21:02.450511+00	3	6	31
37	1	0	0	2019-01-09 06:21:02.571092+00	2019-01-09 06:21:02.571111+00	1	6	29
38	1	0	0	2019-01-09 06:21:02.586607+00	2019-01-09 06:21:02.586633+00	2	6	29
39	1	0	0	2019-01-09 06:21:02.603274+00	2019-01-09 06:21:02.603292+00	3	6	29
40	3	0	0	2019-01-09 06:36:27.314478+00	2019-01-09 06:36:27.314492+00	1	7	28
41	3	0	0	2019-01-09 06:36:27.330396+00	2019-01-09 06:36:27.330413+00	2	7	28
42	3	0	0	2019-01-09 06:36:27.346284+00	2019-01-09 06:36:27.346298+00	3	7	28
43	2	0	0	2019-01-09 06:36:27.491149+00	2019-01-09 06:36:27.491163+00	1	7	31
44	2	0	0	2019-01-09 06:36:27.506267+00	2019-01-09 06:36:27.506281+00	2	7	31
45	2	0	0	2019-01-09 06:36:27.520859+00	2019-01-09 06:36:27.520873+00	3	7	31
46	2	0	0	2019-01-09 06:36:27.661509+00	2019-01-09 06:36:27.661524+00	1	7	29
47	2	0	0	2019-01-09 06:36:27.675988+00	2019-01-09 06:36:27.676002+00	2	7	29
48	2	0	0	2019-01-09 06:36:27.690381+00	2019-01-09 06:36:27.690395+00	3	7	29
49	5	0	0	2019-01-09 06:41:30.284388+00	2019-01-09 06:41:30.284404+00	1	7	28
50	5	0	0	2019-01-09 06:41:30.303036+00	2019-01-09 06:41:30.30305+00	2	7	28
51	5	0	0	2019-01-09 06:41:30.317479+00	2019-01-09 06:41:30.317492+00	3	7	28
52	5	0	0	2019-01-09 06:41:30.331947+00	2019-01-09 06:41:30.331961+00	4	7	28
53	2	0	0	2019-01-09 06:41:30.474075+00	2019-01-09 06:41:30.474089+00	1	7	29
54	2	0	0	2019-01-09 06:41:30.489209+00	2019-01-09 06:41:30.489225+00	2	7	29
55	2	0	0	2019-01-09 06:41:30.504548+00	2019-01-09 06:41:30.504562+00	3	7	29
56	2	0	0	2019-01-09 06:41:30.518862+00	2019-01-09 06:41:30.518876+00	4	7	29
57	4	0	0	2019-01-09 06:41:30.657883+00	2019-01-09 06:41:30.657897+00	1	7	31
58	4	0	0	2019-01-09 06:41:30.672673+00	2019-01-09 06:41:30.672687+00	2	7	31
59	4	0	0	2019-01-09 06:41:30.687354+00	2019-01-09 06:41:30.68737+00	3	7	31
60	4	0	0	2019-01-09 06:41:30.702676+00	2019-01-09 06:41:30.70269+00	4	7	31
61	1	0	0	2019-01-09 08:04:38.726428+00	2019-01-09 08:04:38.726443+00	1	8	28
62	1	0	0	2019-01-09 08:04:38.74204+00	2019-01-09 08:04:38.742057+00	2	8	28
63	1	0	0	2019-01-09 08:04:38.757365+00	2019-01-09 08:04:38.757381+00	3	8	28
64	1	0	0	2019-01-09 08:04:38.772206+00	2019-01-09 08:04:38.77222+00	4	8	28
65	1	0	0	2019-01-09 08:04:38.884994+00	2019-01-09 08:04:38.885013+00	1	8	29
66	1	0	0	2019-01-09 08:04:38.900148+00	2019-01-09 08:04:38.900165+00	2	8	29
67	1	0	0	2019-01-09 08:04:38.91537+00	2019-01-09 08:04:38.915387+00	3	8	29
68	1	0	0	2019-01-09 08:04:38.930458+00	2019-01-09 08:04:38.930472+00	4	8	29
69	1	0	0	2019-01-09 09:24:39.809399+00	2019-01-09 09:24:39.809414+00	1	6	31
70	1	0	0	2019-01-09 09:24:39.829359+00	2019-01-09 09:24:39.829374+00	2	6	31
71	1	0	0	2019-01-09 09:24:39.860958+00	2019-01-09 09:24:39.860979+00	3	6	31
72	1	0	0	2019-01-09 09:24:39.878891+00	2019-01-09 09:24:39.878906+00	4	6	31
73	1	0	0	2019-01-09 09:24:40.096953+00	2019-01-09 09:24:40.096969+00	1	6	29
74	1	0	0	2019-01-09 09:24:40.111749+00	2019-01-09 09:24:40.111763+00	2	6	29
75	1	0	0	2019-01-09 09:24:40.126492+00	2019-01-09 09:24:40.126506+00	3	6	29
76	1	0	0	2019-01-09 09:24:40.141077+00	2019-01-09 09:24:40.141093+00	4	6	29
77	1	0	0	2019-01-09 09:24:40.282991+00	2019-01-09 09:24:40.283004+00	1	6	28
78	1	0	0	2019-01-09 09:24:40.297262+00	2019-01-09 09:24:40.297276+00	2	6	28
79	1	0	0	2019-01-09 09:24:40.313174+00	2019-01-09 09:24:40.313189+00	3	6	28
80	1	0	0	2019-01-09 09:24:40.327946+00	2019-01-09 09:24:40.327961+00	4	6	28
81	1	0	0	2019-01-09 09:24:52.994864+00	2019-01-09 09:24:52.994878+00	1	6	31
82	1	0	0	2019-01-09 09:24:53.01044+00	2019-01-09 09:24:53.010454+00	2	6	31
83	1	0	0	2019-01-09 09:24:53.025387+00	2019-01-09 09:24:53.025401+00	3	6	31
84	1	0	0	2019-01-09 09:24:53.040276+00	2019-01-09 09:24:53.040292+00	4	6	31
85	1	0	0	2019-01-09 09:24:53.187726+00	2019-01-09 09:24:53.187746+00	1	6	29
86	1	0	0	2019-01-09 09:24:53.203838+00	2019-01-09 09:24:53.203861+00	2	6	29
87	1	0	0	2019-01-09 09:24:53.220366+00	2019-01-09 09:24:53.220383+00	4	6	29
88	1	0	0	2019-01-09 09:25:05.925295+00	2019-01-09 09:25:05.925313+00	1	6	31
89	1	0	0	2019-01-09 09:25:05.941676+00	2019-01-09 09:25:05.941695+00	2	6	31
90	1	0	0	2019-01-09 09:25:05.958817+00	2019-01-09 09:25:05.958844+00	3	6	31
91	1	0	0	2019-01-09 09:25:05.975498+00	2019-01-09 09:25:05.97552+00	4	6	31
92	1	0	0	2019-01-09 09:25:06.195139+00	2019-01-09 09:25:06.195157+00	1	6	29
93	1	0	0	2019-01-09 09:25:06.210781+00	2019-01-09 09:25:06.210799+00	2	6	29
94	1	0	0	2019-01-09 09:25:06.2263+00	2019-01-09 09:25:06.226321+00	4	6	29
95	1	0	0	2019-01-09 13:13:47.34529+00	2019-01-09 13:13:47.345304+00	1	9	29
96	1	0	0	2019-01-09 13:13:47.361247+00	2019-01-09 13:13:47.361262+00	2	9	29
97	1	0	0	2019-01-09 13:13:47.376477+00	2019-01-09 13:13:47.376494+00	4	9	29
98	1	0	0	2019-01-09 13:13:52.875061+00	2019-01-09 13:13:52.875077+00	1	9	29
99	1	0	0	2019-01-09 13:13:52.895629+00	2019-01-09 13:13:52.895643+00	2	9	29
100	1	0	0	2019-01-09 13:13:52.911326+00	2019-01-09 13:13:52.91134+00	4	9	29
101	1	0	0	2019-01-09 13:14:48.668033+00	2019-01-09 13:14:48.668049+00	1	9	29
102	1	0	0	2019-01-09 13:14:48.683223+00	2019-01-09 13:14:48.683237+00	2	9	29
103	1	0	0	2019-01-09 13:14:48.698381+00	2019-01-09 13:14:48.698398+00	4	9	29
104	93	0	0	2019-01-09 13:17:43.372313+00	2019-01-09 13:17:43.372327+00	1	10	31
105	93	0	0	2019-01-09 13:17:43.386857+00	2019-01-09 13:17:43.38687+00	2	10	31
106	93	0	0	2019-01-09 13:17:43.401294+00	2019-01-09 13:17:43.401307+00	3	10	31
107	93	0	0	2019-01-09 13:17:43.415733+00	2019-01-09 13:17:43.415747+00	4	10	31
108	91	0	0	2019-01-09 13:18:09.092084+00	2019-01-09 13:18:09.092102+00	1	10	29
109	91	0	0	2019-01-09 13:18:09.107457+00	2019-01-09 13:18:09.107475+00	2	10	29
110	91	0	0	2019-01-09 13:18:09.122449+00	2019-01-09 13:18:09.122463+00	4	10	29
111	91	0	0	2019-01-09 13:18:09.136967+00	2019-01-09 13:18:09.136985+00	3	10	29
\.


--
-- Data for Name: gram_to_brand_po_message; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.gram_to_brand_po_message (id, message, created_at, modified_at, created_by_id) FROM stdin;
\.


--
-- Data for Name: otp_phoneotp; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.otp_phoneotp (id, phone_number, otp, is_verified, attempts, expires_in, created_at, last_otp, resend_in) FROM stdin;
1	9911703645		f	0	300	2019-01-07 12:28:54.271552+00	2019-01-07 12:28:54.27157+00	30
2	8750858087		f	0	300	2019-01-07 16:36:59.732349+00	2019-01-07 16:36:59.732367+00	30
3	8567075678		f	0	300	2019-01-08 06:35:02.253863+00	2019-01-08 06:35:02.253881+00	30
4	9899746673	793732	t	0	300	2019-01-08 12:17:51.900047+00	2019-01-08 12:17:52.707884+00	30
5	9560237858	913126	t	0	300	2019-01-08 12:36:08.046075+00	2019-01-08 12:36:08.083591+00	30
6	7006440794		f	0	300	2019-01-08 12:49:06.432693+00	2019-01-08 12:49:06.432709+00	30
7	9899746673	983918	t	0	300	2019-01-09 06:20:29.833442+00	2019-01-09 06:20:29.887974+00	30
8	7763886418	664306	t	0	300	2019-01-09 07:08:50.052336+00	2019-01-09 07:08:50.111705+00	30
9	9999682701	473551	t	0	300	2019-01-09 08:00:07.196606+00	2019-01-09 08:00:07.252646+00	30
10	9555072423		f	0	300	2019-01-09 09:46:30.795223+00	2019-01-09 09:46:30.79524+00	30
11	9582288240		f	0	300	2019-01-09 10:53:34.115336+00	2019-01-09 10:53:34.115355+00	30
12	7042545165	479631	t	0	300	2019-01-09 11:54:07.571637+00	2019-01-09 11:54:07.797817+00	30
\.


--
-- Data for Name: products_color; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_color (id, color_name, color_code, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: products_flavor; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_flavor (id, flavor_name, flavor_code, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: products_fragrance; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_fragrance (id, fragrance_name, fragrance_code, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: products_packagesize; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_packagesize (id, pack_size_value, pack_size_unit, pack_size_name, pack_length, pack_width, pack_height, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: products_product; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_product (id, product_name, product_slug, product_short_description, product_long_description, product_sku, product_gf_code, product_ean_code, product_inner_case_size, product_case_size, created_at, modified_at, status, product_brand_id) FROM stdin;
28	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-164)	harpic-original-1000ml-harpic-liquid-lemn-200-mlmrp-164	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-164)	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-164)	BTCHLDHRP00000028	GF00629_1	8901396173502	2	8	2019-01-08 08:24:54.438208+00	2019-01-08 08:24:54.454972+00	t	8
270	MAGGI 2-MIN Masala Noodles 70g	maggi-2-min-masala-noodles-70g	MAGGI 2-MIN Masala Noodles 70g	MAGGI 2-MIN Masala Noodles 70g	NPVSBFMAG00000001	GF01521	8.90106E+12	12	96	2019-01-09 04:45:22.586163+00	2019-01-09 04:45:22.604261+00	t	35
29	Harpic Powerplus Original, 200 ml(MRP-36)	harpic-powerplus-original-200-mlmrp-36	Harpic Powerplus Original, 200 ml(MRP-36)	Harpic Powerplus Original, 200 ml(MRP-36)	BTCHLDHRP00000029	GF00661_1	8901396152002	6	48	2019-01-08 08:24:54.471394+00	2019-01-08 08:24:54.4873+00	t	8
30	Harpic Bathroom Cleaner Floral - 500 ml(MRP-84)	harpic-bathroom-cleaner-floral-500-mlmrp-84	Harpic Bathroom Cleaner Floral - 500 ml(MRP-84)	Harpic Bathroom Cleaner Floral - 500 ml(MRP-84)	BTCHLDHRP00000030	GF00667	8901396153108	3	24	2019-01-08 08:24:54.502739+00	2019-01-08 08:24:54.519007+00	t	8
31	Harpic Bathroom Cleaner - Lemon - 500 ml(MRP-84)	harpic-bathroom-cleaner-lemon-500-mlmrp-84	Harpic Bathroom Cleaner - Lemon - 500 ml(MRP-84)	Harpic Bathroom Cleaner - Lemon - 500 ml(MRP-84)	BTCHLDHRP00000031	GF00668	8901396153306	3	24	2019-01-08 08:24:54.533861+00	2019-01-08 08:24:54.550602+00	t	8
32	Harpic Fresh Toilet Cleaner Pine, 500 ml(MRP-78)	harpic-fresh-toilet-cleaner-pine-500-mlmrp-78	Harpic Fresh Toilet Cleaner Pine, 500 ml(MRP-78)	Harpic Fresh Toilet Cleaner Pine, 500 ml(MRP-78)	BTCHLDHRP00000032	GF00658	0	3	24	2019-01-08 08:24:54.565725+00	2019-01-08 08:24:54.581378+00	t	8
33	Harpic Fresh Toilet Cleaner Citrus, 500 ml(MRP-80)	harpic-fresh-toilet-cleaner-citrus-500-mlmrp-80	Harpic Fresh Toilet Cleaner Citrus, 500 ml(MRP-80)	Harpic Fresh Toilet Cleaner Citrus, 500 ml(MRP-80)	BTCHLDHRP00000033	GF00659_1	0	3	24	2019-01-08 08:24:54.597382+00	2019-01-08 08:24:54.612875+00	t	8
34	Harpic Powerplus Toilet Cleaner Rose, 1 L(MRP-156)	harpic-powerplus-toilet-cleaner-rose-1-lmrp-156	Harpic Powerplus Toilet Cleaner Rose, 1 L(MRP-156)	Harpic Powerplus Toilet Cleaner Rose, 1 L(MRP-156)	BTCHLDHRP00000034	GF00622	8901396189602	2	8	2019-01-08 08:24:54.628348+00	2019-01-08 08:24:54.644043+00	t	8
35	Harpic Powerplus Toilet Cleaner Original, 500 ml(MRP-82)	harpic-powerplus-toilet-cleaner-original-500-mlmrp-82	Harpic Powerplus Toilet Cleaner Original, 500 ml(MRP-82)	Harpic Powerplus Toilet Cleaner Original, 500 ml(MRP-82)	BTCHLDHRP00000035	GF00662_1	8901396151005	3	24	2019-01-08 08:24:54.658971+00	2019-01-08 08:24:54.675855+00	t	8
36	Harpic Powerplus Toilet Cleaner Original, 500 ml+ 30% Extra(MRP-82)	harpic-powerplus-toilet-cleaner-original-500-ml-30-extramrp-82	Harpic Powerplus Toilet Cleaner Original, 500 ml+ 30% Extra(MRP-82)	Harpic Powerplus Toilet Cleaner Original, 500 ml+ 30% Extra(MRP-82)	BTCHLDHRP00000036	GF00663_1	8901396151005	3	18	2019-01-08 08:24:54.690843+00	2019-01-08 08:24:54.707278+00	t	8
37	Harpic Powerplus Toilet Cleaner Orange, 500 ml(MRP-82)	harpic-powerplus-toilet-cleaner-orange-500-mlmrp-82	Harpic Powerplus Toilet Cleaner Orange, 500 ml(MRP-82)	Harpic Powerplus Toilet Cleaner Orange, 500 ml(MRP-82)	BTCHLDHRP00000037	GF00635_1	8901396151463	3	24	2019-01-08 08:24:54.721662+00	2019-01-08 08:24:54.737209+00	t	8
38	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-168)	harpic-original-1000ml-harpic-liquid-lemn-200-mlmrp-168	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-168)	Harpic, Original- 1000ml + Harpic Liquid, Lemn- 200 ml(MRP-168)	BTCHLDHRP00000038	GF00629_2	8901396173502	2	8	2019-01-08 08:24:54.752035+00	2019-01-08 08:24:54.767775+00	t	8
39	Harpic Powerplus Toilet Cleaner Orange, 1 l(MRP-160)	harpic-powerplus-toilet-cleaner-orange-1-lmrp-160	Harpic Powerplus Toilet Cleaner Orange, 1 l(MRP-160)	Harpic Powerplus Toilet Cleaner Orange, 1 l(MRP-160)	BTCHLDHRP00000039	GF00624_2	8901396189800	2	8	2019-01-08 08:24:54.782487+00	2019-01-08 08:24:54.798446+00	t	8
40	Harpic Powerplus Toilet Cleaner Rose, 1 L all in one(MRP-160)	harpic-powerplus-toilet-cleaner-rose-1-l-all-in-onemrp-160	Harpic Powerplus Toilet Cleaner Rose, 1 L all in one(MRP-160)	Harpic Powerplus Toilet Cleaner Rose, 1 L all in one(MRP-160)	BTCHLDHRP00000040	GF00622_1	8901396189602	2	8	2019-01-08 08:24:54.813483+00	2019-01-08 08:24:54.833134+00	t	8
41	Cherry Blossom Wax Polish Black 40 gm(MRP-55)	cherry-blossom-wax-polish-black-40-gmmrp-55	Cherry Blossom Wax Polish Black 40 gm(MRP-55)	Cherry Blossom Wax Polish Black 40 gm(MRP-55)	SHCHLDCHR00000001	GF00712_2	8.90E+12	3	216	2019-01-08 14:12:04.026452+00	2019-01-08 14:12:04.04455+00	t	29
42	Cherry Blossom Wax Polish Black 15 gm(MRP-30)	cherry-blossom-wax-polish-black-15-gmmrp-30	Cherry Blossom Wax Polish Black 15 gm(MRP-30)	Cherry Blossom Wax Polish Black 15 gm(MRP-30)	SHCHLDCHR00000002	GF00711_1	8.90E+12	6	432	2019-01-08 14:12:04.062027+00	2019-01-08 14:12:04.083891+00	t	29
43	Clinic Plus Shampoo 6 ML (MRP-1)	clinic-plus-shampoo-6-ml-mrp-1	Clinic Plus Shampoo 6 ML (MRP-1)	Clinic Plus Shampoo 6 ML (MRP-1)	HRCPCRCLI00000001	GF01161	8.90E+12	16	960	2019-01-08 14:12:04.101301+00	2019-01-08 14:12:04.11882+00	t	77
44	CLOSEUP RED HOT ACTIVE GEL TP 24G+20% EXTRA(MRP-10)	closeup-red-hot-active-gel-tp-24g20-extramrp-10	CLOSEUP RED HOT ACTIVE GEL TP 24G+20% EXTRA(MRP-10)	CLOSEUP RED HOT ACTIVE GEL TP 24G+20% EXTRA(MRP-10)	ORCPCRCLP00000001	GF01187	8.90E+12	12	288	2019-01-08 14:12:04.134843+00	2019-01-08 14:12:04.157475+00	t	76
45	Colgate dental cream  150g(MRP-65)	colgate-dental-cream-150gmrp-65	Colgate dental cream  150g(MRP-65)	Colgate dental cream  150g(MRP-65)	ORCPCRCLB00000001	GF01567	8.90E+12	2	96	2019-01-08 14:12:04.173786+00	2019-01-08 14:12:04.191248+00	t	75
46	Colgate Dental Cream 54g(MRP-20)	colgate-dental-cream-54gmrp-20	Colgate Dental Cream 54g(MRP-20)	Colgate Dental Cream 54g(MRP-20)	ORCPCRCLB00000002	GF01569	8.90E+12	6	288	2019-01-08 14:12:04.207472+00	2019-01-08 14:12:04.230465+00	t	75
47	Colgate Dental cream 21g Hanger pack(MRP-10)	colgate-dental-cream-21g-hanger-packmrp-10	Colgate Dental cream 21g Hanger pack(MRP-10)	Colgate Dental cream 21g Hanger pack(MRP-10)	ORCPCRCLB00000003	GF01571	8.90E+12	12	288	2019-01-08 14:12:04.246793+00	2019-01-08 14:12:04.264796+00	t	75
48	Colgate  Maxfresh Red Tp 80G(MRP-48)	colgate-maxfresh-red-tp-80gmrp-48	Colgate  Maxfresh Red Tp 80G(MRP-48)	Colgate  Maxfresh Red Tp 80G(MRP-48)	ORCPCRCLB00000004	GF01570	8.90E+12	4	96	2019-01-08 14:12:04.281343+00	2019-01-08 14:12:04.302585+00	t	75
49	Colgate dental cream  100g(MRP-49)	colgate-dental-cream-100gmrp-49	Colgate dental cream  100g(MRP-49)	Colgate dental cream  100g(MRP-49)	ORCPCRCLB00000005	GF01568	8.90E+12	3	144	2019-01-08 14:12:04.318776+00	2019-01-08 14:12:04.337174+00	t	75
50	Colgate  Kids 0-2 SINGLE  Toothbrush(MRP-30)	colgate-kids-0-2-single-toothbrushmrp-30	Colgate  Kids 0-2 SINGLE  Toothbrush(MRP-30)	Colgate  Kids 0-2 SINGLE  Toothbrush(MRP-30)	ORCPCRCLB00000006	GF01559	8.90E+12	6	72	2019-01-08 14:12:04.353634+00	2019-01-08 14:12:04.370428+00	t	75
51	Colgate Cibaca 123  SINGLE Toothbrush (MRP-13)	colgate-cibaca-123-single-toothbrush-mrp-13	Colgate Cibaca 123  SINGLE Toothbrush (MRP-13)	Colgate Cibaca 123  SINGLE Toothbrush (MRP-13)	ORCPCRCLB00000007	GF01564	8.90E+12	6	288	2019-01-08 14:12:04.38693+00	2019-01-08 14:12:04.404031+00	t	75
52	Colgate  Kids2+   SINGLE Toothbrush(MRP-25)	colgate-kids2-single-toothbrushmrp-25	Colgate  Kids2+   SINGLE Toothbrush(MRP-25)	Colgate  Kids2+   SINGLE Toothbrush(MRP-25)	ORCPCRCLB00000008	GF01560	8.90E+12	6	288	2019-01-08 14:12:04.420545+00	2019-01-08 14:12:04.440403+00	t	75
53	Colgate Zig Zag Black 6 pc hanger Soft(MRP-25)	colgate-zig-zag-black-6-pc-hanger-softmrp-25	Colgate Zig Zag Black 6 pc hanger Soft(MRP-25)	Colgate Zig Zag Black 6 pc hanger Soft(MRP-25)	ORCPCRCLB00000009	GF01566_1		6	288	2019-01-08 14:12:04.456059+00	2019-01-08 14:12:04.473084+00	t	75
54	Colgate  Sup Flexi Black soft SINGLE  Toothbrush(MRP-20)	colgate-sup-flexi-black-soft-single-toothbrushmrp-20	Colgate  Sup Flexi Black soft SINGLE  Toothbrush(MRP-20)	Colgate  Sup Flexi Black soft SINGLE  Toothbrush(MRP-20)	ORCPCRCLB00000010	GF01563		12	288	2019-01-08 14:12:04.490191+00	2019-01-08 14:12:04.508688+00	t	75
55	Colgate Zig Zag Black 6 pc hanger Medium(MRP-30)+ Ved Shakti Rs-10	colgate-zig-zag-black-6-pc-hanger-mediummrp-30-ved-shakti-rs-10	Colgate Zig Zag Black 6 pc hanger Medium(MRP-30)+ Ved Shakti Rs-10	Colgate Zig Zag Black 6 pc hanger Medium(MRP-30)+ Ved Shakti Rs-10	ORCPCRCLB00000011	GF01594		6	288	2019-01-08 14:12:04.524594+00	2019-01-08 14:12:04.542029+00	t	75
56	Colin Glass Cleaner Pump - 250 ml(MRP-56)	colin-glass-cleaner-pump-250-mlmrp-56	Colin Glass Cleaner Pump - 250 ml(MRP-56)	Colin Glass Cleaner Pump - 250 ml(MRP-56)	GLCHLDCLN00000001	GF00649	8.90E+12	6	48	2019-01-08 14:12:04.558684+00	2019-01-08 14:12:04.575117+00	t	74
57	Colin Glass Cleaner Pump 2X More Shine  500ml (MRP-85)	colin-glass-cleaner-pump-2x-more-shine-500ml-mrp-85	Colin Glass Cleaner Pump 2X More Shine  500ml (MRP-85)	Colin Glass Cleaner Pump 2X More Shine  500ml (MRP-85)	GLCHLDCLN00000002	GF00648_1	8.90E+12	5	25	2019-01-08 14:12:04.590895+00	2019-01-08 14:12:04.607646+00	t	74
58	Dabur Almond Hair Oil, 100ml(MRP-63)	dabur-almond-hair-oil-100mlmrp-63	Dabur Almond Hair Oil, 100ml(MRP-63)	Dabur Almond Hair Oil, 100ml(MRP-63)	HRCPCRDAL00000001	GF01635	89005910	3	48	2019-01-08 14:12:04.622787+00	2019-01-08 14:12:04.639884+00	t	73
59	Dabur Amla Hair Oil 90ml(MRP-44)	dabur-amla-hair-oil-90mlmrp-44	Dabur Amla Hair Oil 90ml(MRP-44)	Dabur Amla Hair Oil 90ml(MRP-44)	HRCPCRDAM00000001	GF01636	89006825	3	60	2019-01-08 14:12:04.656147+00	2019-01-08 14:12:04.673447+00	t	9
60	Dabur Amla Hair Oil - 180ml(MRP-88)	dabur-amla-hair-oil-180mlmrp-88	Dabur Amla Hair Oil - 180ml(MRP-88)	Dabur Amla Hair Oil - 180ml(MRP-88)	HRCPCRDAM00000002	GF01637	8.90E+12	2	36	2019-01-08 14:12:04.690166+00	2019-01-08 14:12:04.707074+00	t	9
61	Dabur Red Ayurvedic Paste 100 gm (MRP-50)	dabur-red-ayurvedic-paste-100-gm-mrp-50	Dabur Red Ayurvedic Paste 100 gm (MRP-50)	Dabur Red Ayurvedic Paste 100 gm (MRP-50)	ORCPCRDRE00000001	GF01646	8.90E+12	3	72	2019-01-08 14:12:04.724266+00	2019-01-08 14:12:04.740866+00	t	10
62	Dabur Red Paste 50gm(MRP-20)	dabur-red-paste-50gmmrp-20	Dabur Red Paste 50gm(MRP-20)	Dabur Red Paste 50gm(MRP-20)	ORCPCRDRE00000002	GF01647	8.90E+12	12	144	2019-01-08 14:12:04.757285+00	2019-01-08 14:12:04.774029+00	t	10
63	Dabur Red Ayurvedic Paste 200 g(MRP-95)	dabur-red-ayurvedic-paste-200-gmrp-95	Dabur Red Ayurvedic Paste 200 g(MRP-95)	Dabur Red Ayurvedic Paste 200 g(MRP-95)	ORCPCRDRE00000003	GF01648	8.90E+12	2	36	2019-01-08 14:12:04.790292+00	2019-01-08 14:12:04.807185+00	t	10
64	Dettol Liquid Handwash Original - 175 ml x 3(MRP-122)	dettol-liquid-handwash-original-175-ml-x-3mrp-122	Dettol Liquid Handwash Original - 175 ml x 3(MRP-122)	Dettol Liquid Handwash Original - 175 ml x 3(MRP-122)	HWSPCRDET00000001	GF00578	8.90E+12	2	16	2019-01-08 14:12:04.825821+00	2019-01-08 14:12:04.846752+00	t	30
65	Dettol Original Soap, 125g (Pack of 4)(MRP-165)	dettol-original-soap-125g-pack-of-4mrp-165	Dettol Original Soap, 125g (Pack of 4)(MRP-165)	Dettol Original Soap, 125g (Pack of 4)(MRP-165)	BBSPCRDET00000001	GF00584	8.90E+12	2	30	2019-01-08 14:12:04.864051+00	2019-01-08 14:12:04.882666+00	t	30
66	Dettol Original Soap, 75g (Pack of 4)(MRP-103)	dettol-original-soap-75g-pack-of-4mrp-103	Dettol Original Soap, 75g (Pack of 4)(MRP-103)	Dettol Original Soap, 75g (Pack of 4)(MRP-103)	BBSPCRDET00000002	GF00586	8.90E+12	2	48	2019-01-08 14:12:04.90008+00	2019-01-08 14:12:04.918308+00	t	30
67	Dettol Original Soap - 45 g(MRP-10)	dettol-original-soap-45-gmrp-10	Dettol Original Soap - 45 g(MRP-10)	Dettol Original Soap - 45 g(MRP-10)	BBSPCRDET00000003	GF00573	8.90E+12	15	300	2019-01-08 14:12:04.934677+00	2019-01-08 14:12:04.951685+00	t	30
68	Dettol lather shaving cream 60g+18gfree_78g(MRP-75)	dettol-lather-shaving-cream-60g18gfree_78gmrp-75	Dettol lather shaving cream 60g+18gfree_78g(MRP-75)	Dettol lather shaving cream 60g+18gfree_78g(MRP-75)	SVNPCRDET00000001	GF00601	8.90E+12	6	144	2019-01-08 14:12:04.967778+00	2019-01-08 14:12:04.983918+00	t	30
69	Dettol Cool Shaving Cream 60g+18gfree_78g(MRP-75)	dettol-cool-shaving-cream-60g18gfree_78gmrp-75	Dettol Cool Shaving Cream 60g+18gfree_78g(MRP-75)	Dettol Cool Shaving Cream 60g+18gfree_78g(MRP-75)	SVNPCRDET00000002	GF00602	8.90E+12	6	144	2019-01-08 14:12:05.005337+00	2019-01-08 14:12:05.05003+00	t	30
70	Dettol Cool Soap, 75g (Pack of 4) (MRP-103)	dettol-cool-soap-75g-pack-of-4-mrp-103	Dettol Cool Soap, 75g (Pack of 4) (MRP-103)	Dettol Cool Soap, 75g (Pack of 4) (MRP-103)	BBSPCRDET00000004	GF00657	8.90E+12	1	48	2019-01-08 14:12:05.065447+00	2019-01-08 14:12:05.083726+00	t	30
71	Dettol Cool Soap - 45 g(MRP-10)	dettol-cool-soap-45-gmrp-10	Dettol Cool Soap - 45 g(MRP-10)	Dettol Cool Soap - 45 g(MRP-10)	BBSPCRDET00000005	GF00727		15	300	2019-01-08 14:12:05.100892+00	2019-01-08 14:12:05.117853+00	t	30
72	Dettol cool soap 125g (Buy 3+Get 1 free of 125g cool soap) (MRP-165)	dettol-cool-soap-125g-buy-3get-1-free-of-125g-cool-soap-mrp-165	Dettol cool soap 125g (Buy 3+Get 1 free of 125g cool soap) (MRP-165)	Dettol cool soap 125g (Buy 3+Get 1 free of 125g cool soap) (MRP-165)	BBSPCRDET00000006	GF00731	8.90E+12	2	30	2019-01-08 14:12:05.133724+00	2019-01-08 14:12:05.151006+00	t	30
73	Dettol Soap Original Soap - 75gm(MRP-31)	dettol-soap-original-soap-75gmmrp-31	Dettol Soap Original Soap - 75gm(MRP-31)	Dettol Soap Original Soap - 75gm(MRP-31)	BBSPCRDET00000007	GF00620	8.90E+12	4	192	2019-01-08 14:12:05.166145+00	2019-01-08 14:12:05.183477+00	t	30
74	Dettol Liquid Handwash (Skincare) - 200 ml Free Liquid Handwash - 175 ml(MRP-95)	dettol-liquid-handwash-skincare-200-ml-free-liquid-handwash-175-mlmrp-95	Dettol Liquid Handwash (Skincare) - 200 ml Free Liquid Handwash - 175 ml(MRP-95)	Dettol Liquid Handwash (Skincare) - 200 ml Free Liquid Handwash - 175 ml(MRP-95)	HWSPCRDET00000002	GF00726	8.90E+12	1	24	2019-01-08 14:12:05.20073+00	2019-01-08 14:12:05.217324+00	t	30
75	Dettol Liquid Handwash Skincare - 175 ml x 3(MRP-122)	dettol-liquid-handwash-skincare-175-ml-x-3mrp-122	Dettol Liquid Handwash Skincare - 175 ml x 3(MRP-122)	Dettol Liquid Handwash Skincare - 175 ml x 3(MRP-122)	HWSPCRDET00000003	GF00583	8.90E+12	2	16	2019-01-08 14:12:05.234522+00	2019-01-08 14:12:05.251395+00	t	30
76	Dettol Liquid Handwash Cool - 175 ml x 3(MRP-146)	dettol-liquid-handwash-cool-175-ml-x-3mrp-146	Dettol Liquid Handwash Cool - 175 ml x 3(MRP-146)	Dettol Liquid Handwash Cool - 175 ml x 3(MRP-146)	HWSPCRDET00000004	GF00589	8.90E+12	2	16	2019-01-08 14:12:05.267027+00	2019-01-08 14:12:05.284822+00	t	30
77	Dettol Kitchen Dish and Slab Gel - 400 ml (Lemon Fresh)(MRP-131)	dettol-kitchen-dish-and-slab-gel-400-ml-lemon-freshmrp-131	Dettol Kitchen Dish and Slab Gel - 400 ml (Lemon Fresh)(MRP-131)	Dettol Kitchen Dish and Slab Gel - 400 ml (Lemon Fresh)(MRP-131)	DWSHLDDET00000001	GF00594	8.90E+12	1	24	2019-01-08 14:12:05.30022+00	2019-01-08 14:12:05.318844+00	t	30
78	Dettol Kitchen Dish and Slab Gel - 400 ml (Lime Splash)(MRP-119)	dettol-kitchen-dish-and-slab-gel-400-ml-lime-splashmrp-119	Dettol Kitchen Dish and Slab Gel - 400 ml (Lime Splash)(MRP-119)	Dettol Kitchen Dish and Slab Gel - 400 ml (Lime Splash)(MRP-119)	DWSHLDDET00000002	GF00596	8.90E+12	1	24	2019-01-08 14:12:05.335524+00	2019-01-08 14:12:05.35225+00	t	30
79	Dettol Instant Hand Sanitizer - 50 ml(MRP-77)	dettol-instant-hand-sanitizer-50-mlmrp-77	Dettol Instant Hand Sanitizer - 50 ml(MRP-77)	Dettol Instant Hand Sanitizer - 50 ml(MRP-77)	HWSPCRDET00000005	GF00612	8.90E+12	3	96	2019-01-08 14:12:05.368637+00	2019-01-08 14:12:05.39267+00	t	30
80	Dettol Soap, Skincare - 125gm(MRP-53)	dettol-soap-skincare-125gmmrp-53	Dettol Soap, Skincare - 125gm(MRP-53)	Dettol Soap, Skincare - 125gm(MRP-53)	BBSPCRDET00000008	GF00729_1	8.90E+12	4	120	2019-01-08 14:12:05.412694+00	2019-01-08 14:12:05.42922+00	t	30
108	GHARI DETERGENT CAKE MRP 10/-	ghari-detergent-cake-mrp-10-	GHARI DETERGENT CAKE MRP 10/-	GHARI DETERGENT CAKE MRP 10/-	DETHLDGHD00000001	GF01408	8.90E+12	7	56	2019-01-08 14:12:06.354313+00	2019-01-08 14:12:06.37153+00	t	3
271	MAGGI Pichkoo Hot & Sweet Doy	maggi-pichkoo-hot-sweet-doy	MAGGI Pichkoo Hot & Sweet Doy	MAGGI Pichkoo Hot & Sweet Doy	KSCSBFMAG00000001	GF01524	8.90106E+12	6	72	2019-01-09 04:45:22.62197+00	2019-01-09 04:45:22.642661+00	t	35
81	Dettol Skincare pH Balance Handwash Refill Pouch, 175ml(MRP-54)	dettol-skincare-ph-balance-handwash-refill-pouch-175mlmrp-54	Dettol Skincare pH Balance Handwash Refill Pouch, 175ml(MRP-54)	Dettol Skincare pH Balance Handwash Refill Pouch, 175ml(MRP-54)	HWSPCRDET00000006	GF00581_1	8.90E+12	3	48	2019-01-08 14:12:05.445313+00	2019-01-08 14:12:05.462163+00	t	30
82	Dettol Kitchen Dish and Slab Gel - 750 ml (Lemon Fresh)(MRP-192)	dettol-kitchen-dish-and-slab-gel-750-ml-lemon-freshmrp-192	Dettol Kitchen Dish and Slab Gel - 750 ml (Lemon Fresh)(MRP-192)	Dettol Kitchen Dish and Slab Gel - 750 ml (Lemon Fresh)(MRP-192)	DWSHLDDET00000003	GF00595	8.90E+12	1	12	2019-01-08 14:12:05.477434+00	2019-01-08 14:12:05.493626+00	t	30
83	Dettol Kitchen Dish and Slab Gel - 750 ml (Lime Splash)(MRP-192)	dettol-kitchen-dish-and-slab-gel-750-ml-lime-splashmrp-192	Dettol Kitchen Dish and Slab Gel - 750 ml (Lime Splash)(MRP-192)	Dettol Kitchen Dish and Slab Gel - 750 ml (Lime Splash)(MRP-192)	DWSHLDDET00000004	GF00597	8.90E+12	1	12	2019-01-08 14:12:05.509672+00	2019-01-08 14:12:05.525871+00	t	30
84	Dettol Disinfectant Multi-Use Hygiene Liquid - 200 ml(MRP-83)	dettol-disinfectant-multi-use-hygiene-liquid-200-mlmrp-83	Dettol Disinfectant Multi-Use Hygiene Liquid - 200 ml(MRP-83)	Dettol Disinfectant Multi-Use Hygiene Liquid - 200 ml(MRP-83)	HWSPCRDET00000007	GF00607	8.90E+12	2	48	2019-01-08 14:12:05.541748+00	2019-01-08 14:12:05.558429+00	t	30
85	Dettol Soap, Skincare, 75 g(MRP-32)	dettol-soap-skincare-75-gmrp-32	Dettol Soap, Skincare, 75 g(MRP-32)	Dettol Soap, Skincare, 75 g(MRP-32)	BBSPCRDET00000009	GF00621	8.90E+12	6	192	2019-01-08 14:12:05.574141+00	2019-01-08 14:12:05.590848+00	t	30
86	Dettol Soap, Cool - 125gm(MRP-53)	dettol-soap-cool-125gmmrp-53	Dettol Soap, Cool - 125gm(MRP-53)	Dettol Soap, Cool - 125gm(MRP-53)	BBSPCRDET00000010	GF00730_1	8.90E+12	3	120	2019-01-08 14:12:05.607412+00	2019-01-08 14:12:05.625835+00	t	30
87	Dettol Bathing Bar Soap, Aloe - 100gm (Pack of 3)(MRP-112)	dettol-bathing-bar-soap-aloe-100gm-pack-of-3mrp-112	Dettol Bathing Bar Soap, Aloe - 100gm (Pack of 3)(MRP-112)	Dettol Bathing Bar Soap, Aloe - 100gm (Pack of 3)(MRP-112)	BBSPCRDET00000011	GF01017	8.90E+12	1	48	2019-01-08 14:12:05.643692+00	2019-01-08 14:12:05.66009+00	t	30
88	Dettol Bathing Bar Soap, Aloe - 100gm(MRP-39)	dettol-bathing-bar-soap-aloe-100gmmrp-39	Dettol Bathing Bar Soap, Aloe - 100gm(MRP-39)	Dettol Bathing Bar Soap, Aloe - 100gm(MRP-39)	BBSPCRDET00000012	GF01016	8.90E+12	6	144	2019-01-08 14:12:05.676272+00	2019-01-08 14:12:05.695403+00	t	30
89	Dettol Skincare soap 125g (Buy 3+Get 1 free of 125g Skincare soap) (MRP-165)	dettol-skincare-soap-125g-buy-3get-1-free-of-125g-skincare-soap-mrp-165	Dettol Skincare soap 125g (Buy 3+Get 1 free of 125g Skincare soap) (MRP-165)	Dettol Skincare soap 125g (Buy 3+Get 1 free of 125g Skincare soap) (MRP-165)	BBSPCRDET00000013	GF01290	8.90E+12	1	30	2019-01-08 14:12:05.710523+00	2019-01-08 14:12:05.728917+00	t	30
90	Dettol Skincare Soap, 75g (Pack of 4)(MRP-103)	dettol-skincare-soap-75g-pack-of-4mrp-103	Dettol Skincare Soap, 75g (Pack of 4)(MRP-103)	Dettol Skincare Soap, 75g (Pack of 4)(MRP-103)	BBSPCRDET00000014	GF01291		2	48	2019-01-08 14:12:05.745011+00	2019-01-08 14:12:05.766465+00	t	30
91	Dettol LHW (Original) - 200 ml  with Free LHW - 175 ml(MRP-99)	dettol-lhw-original-200-ml-with-free-lhw-175-mlmrp-99	Dettol LHW (Original) - 200 ml  with Free LHW - 175 ml(MRP-99)	Dettol LHW (Original) - 200 ml  with Free LHW - 175 ml(MRP-99)	HWSPCRDET00000008	GF00636_2	8.90E+12	1	24	2019-01-08 14:12:05.782751+00	2019-01-08 14:12:05.803605+00	t	30
92	DOVE CREAM BEAUTY BATHING BAR 50G(MRP-25)	dove-cream-beauty-bathing-bar-50gmrp-25	DOVE CREAM BEAUTY BATHING BAR 50G(MRP-25)	DOVE CREAM BEAUTY BATHING BAR 50G(MRP-25)	BBSPCRDOV00000001	GF01192	8.90E+12	6	72	2019-01-08 14:12:05.819863+00	2019-01-08 14:12:05.838841+00	t	18
93	Dove Shampoo Straight & Silky Shampoo 6ml(MRP-2)	dove-shampoo-straight-silky-shampoo-6mlmrp-2	Dove Shampoo Straight & Silky Shampoo 6ml(MRP-2)	Dove Shampoo Straight & Silky Shampoo 6ml(MRP-2)	HRCPCRDOV00000001	GF01168	8.90E+12	16	960	2019-01-08 14:12:05.854222+00	2019-01-08 14:12:05.871028+00	t	18
94	Dove Hair fall Rescue Shampoo 6ml(MRP-2)	dove-hair-fall-rescue-shampoo-6mlmrp-2	Dove Hair fall Rescue Shampoo 6ml(MRP-2)	Dove Hair fall Rescue Shampoo 6ml(MRP-2)	HRCPCRDOV00000002	GF01169	8.90E+12	16	960	2019-01-08 14:12:05.886572+00	2019-01-08 14:12:05.903154+00	t	18
95	Dove Intense Repair Shampoo 6ml(MRP-2)	dove-intense-repair-shampoo-6mlmrp-2	Dove Intense Repair Shampoo 6ml(MRP-2)	Dove Intense Repair Shampoo 6ml(MRP-2)	HRCPCRDOV00000003	GF01170	8.90E+12	16	960	2019-01-08 14:12:05.918951+00	2019-01-08 14:12:05.935592+00	t	18
96	Dove Hair fall Rescue Shampoo 6ml+ 25%(MRP-3)	dove-hair-fall-rescue-shampoo-6ml-25mrp-3	Dove Hair fall Rescue Shampoo 6ml+ 25%(MRP-3)	Dove Hair fall Rescue Shampoo 6ml+ 25%(MRP-3)	HRCPCRDOV00000004	GF01438	8.90E+12	16	960	2019-01-08 14:12:05.951553+00	2019-01-08 14:12:05.968954+00	t	18
97	Dove Intense Repair Shampoo 6ml+ 25%(MRP-3)	dove-intense-repair-shampoo-6ml-25mrp-3	Dove Intense Repair Shampoo 6ml+ 25%(MRP-3)	Dove Intense Repair Shampoo 6ml+ 25%(MRP-3)	HRCPCRDOV00000005	GF01439		16	960	2019-01-08 14:12:05.984191+00	2019-01-08 14:12:06.006019+00	t	18
98	Engage Men Mate Deo 165 ml(MRP-190)	engage-men-mate-deo-165-mlmrp-190	Engage Men Mate Deo 165 ml(MRP-190)	Engage Men Mate Deo 165 ml(MRP-190)	DEOPCRENG00000001	GF00743	8.90E+12	2	12	2019-01-08 14:12:06.023182+00	2019-01-08 14:12:06.041021+00	t	72
99	Engage Women Blush Deo 165 ml(MRP-190)	engage-women-blush-deo-165-mlmrp-190	Engage Women Blush Deo 165 ml(MRP-190)	Engage Women Blush Deo 165 ml(MRP-190)	DEOPCRENG00000002	GF00758	8.90E+12	2	12	2019-01-08 14:12:06.05741+00	2019-01-08 14:12:06.075839+00	t	72
100	Engage Sports Fresh Deo Him 165 ml(MRP-190)	engage-sports-fresh-deo-him-165-mlmrp-190	Engage Sports Fresh Deo Him 165 ml(MRP-190)	Engage Sports Fresh Deo Him 165 ml(MRP-190)	DEOPCRENG00000003	GF00820		2	12	2019-01-08 14:12:06.090896+00	2019-01-08 14:12:06.109962+00	t	72
101	Fair & Lovely Mulivitamin 4.5gm(MRP-5)	fair-lovely-mulivitamin-45gmmrp-5	Fair & Lovely Mulivitamin 4.5gm(MRP-5)	Fair & Lovely Mulivitamin 4.5gm(MRP-5)	SKCPCRFAL00000001	GF01176	8.90E+12	12	576	2019-01-08 14:12:06.126615+00	2019-01-08 14:12:06.142694+00	t	19
102	Fair & Lovely Advance Mulivitamin 15gm(MRP-20)	fair-lovely-advance-mulivitamin-15gmmrp-20	Fair & Lovely Advance Mulivitamin 15gm(MRP-20)	Fair & Lovely Advance Mulivitamin 15gm(MRP-20)	SKCPCRFAL00000002	GF01190	8.90E+12	4	144	2019-01-08 14:12:06.158091+00	2019-01-08 14:12:06.174212+00	t	19
103	Fair & Lovely Advance Mulivitamin 9gm(MRP-8)	fair-lovely-advance-mulivitamin-9gmmrp-8	Fair & Lovely Advance Mulivitamin 9gm(MRP-8)	Fair & Lovely Advance Mulivitamin 9gm(MRP-8)	SKCPCRFAL00000003	GF01179	8.90E+12	24	576	2019-01-08 14:12:06.190345+00	2019-01-08 14:12:06.207196+00	t	19
104	FENA DETERGENT POWDER 500 GM(MRP-30)	fena-detergent-powder-500-gmmrp-30	FENA DETERGENT POWDER 500 GM(MRP-30)	FENA DETERGENT POWDER 500 GM(MRP-30)	DETHLDFNA00000001	GF01120	8.90E+12	5	50	2019-01-08 14:12:06.222292+00	2019-01-08 14:12:06.239331+00	t	2
105	FENA DETERGENT CAKE 210 GM(MRP-10)	fena-detergent-cake-210-gmmrp-10	FENA DETERGENT CAKE 210 GM(MRP-10)	FENA DETERGENT CAKE 210 GM(MRP-10)	DETHLDFNA00000002	GF01123	8.90E+12	8	64	2019-01-08 14:12:06.254545+00	2019-01-08 14:12:06.27166+00	t	2
106	FENA DETERGENT CAKE 105 GM(MRP-5)	fena-detergent-cake-105-gmmrp-5	FENA DETERGENT CAKE 105 GM(MRP-5)	FENA DETERGENT CAKE 105 GM(MRP-5)	DETHLDFNA00000003	GF01124	8.90E+12	10	100	2019-01-08 14:12:06.287413+00	2019-01-08 14:12:06.30437+00	t	2
107	FENA DETERGENT POWDER  150 GM(MRP-10)	fena-detergent-powder-150-gmmrp-10	FENA DETERGENT POWDER  150 GM(MRP-10)	FENA DETERGENT POWDER  150 GM(MRP-10)	DETHLDFNA00000004	GF01128	8.90E+12	12	84	2019-01-08 14:12:06.319668+00	2019-01-08 14:12:06.337807+00	t	2
109	GHARI DETERGENT CAKE MRP 5/-	ghari-detergent-cake-mrp-5-	GHARI DETERGENT CAKE MRP 5/-	GHARI DETERGENT CAKE MRP 5/-	DETHLDGHD00000002	GF01422	8.90E+12	10	100	2019-01-08 14:12:06.386994+00	2019-01-08 14:12:06.404671+00	t	3
110	GHARI DETERGENT PWDER MRP 10/-	ghari-detergent-pwder-mrp-10-	GHARI DETERGENT PWDER MRP 10/-	GHARI DETERGENT PWDER MRP 10/-	DETHLDGHD00000003	GF01409	8.90E+12	8	80	2019-01-08 14:12:06.420982+00	2019-01-08 14:12:06.437423+00	t	3
111	GHARI DETERGENT PWDER MRP 28/-	ghari-detergent-pwder-mrp-28-	GHARI DETERGENT PWDER MRP 28/-	GHARI DETERGENT PWDER MRP 28/-	DETHLDGHD00000004	GF01410	8.90E+12	8	40	2019-01-08 14:12:06.452366+00	2019-01-08 14:12:06.46988+00	t	3
112	Ghari Detergent Powder 1KG MRP 55/-	ghari-detergent-powder-1kg-mrp-55-	Ghari Detergent Powder 1KG MRP 55/-	Ghari Detergent Powder 1KG MRP 55/-	DETHLDGHD00000005	GF01595		5	25	2019-01-08 14:12:06.487324+00	2019-01-08 14:12:06.503937+00	t	3
113	Gillete Gurad Cart MRP-10 Pack of 8	gillete-gurad-cart-mrp-10-pack-of-8	Gillete Gurad Cart MRP-10 Pack of 8	Gillete Gurad Cart MRP-10 Pack of 8	SVNPCRGIL00000001	GF01025	4.90E+12	1	300	2019-01-08 14:12:06.519166+00	2019-01-08 14:12:06.53546+00	t	78
114	Gillete Presto (MRP-19)	gillete-presto-mrp-19	Gillete Presto (MRP-19)	Gillete Presto (MRP-19)	SVNPCRGIL00000002	GF01026	4.90E+12	12	768	2019-01-08 14:12:06.55086+00	2019-01-08 14:12:06.567735+00	t	78
115	Godrej Expert Hair Colour - Natural Black 1, Multi Pack (MRP-99)	godrej-expert-hair-colour-natural-black-1-multi-pack-mrp-99	Godrej Expert Hair Colour - Natural Black 1, Multi Pack (MRP-99)	Godrej Expert Hair Colour - Natural Black 1, Multi Pack (MRP-99)	HRCPCRGEX00000001	GF00053	8.90E+12	3	36	2019-01-08 14:12:06.582736+00	2019-01-08 14:12:06.598765+00	t	14
116	Godrej Expert Rich Creme Hair Colour Burgundy (4.16) (MRP-30)	godrej-expert-rich-creme-hair-colour-burgundy-416-mrp-30	Godrej Expert Rich Creme Hair Colour Burgundy (4.16) (MRP-30)	Godrej Expert Rich Creme Hair Colour Burgundy (4.16) (MRP-30)	HRCPCRGEX00000002	GF00054	8.90E+12	6	192	2019-01-08 14:12:06.614271+00	2019-01-08 14:12:06.630099+00	t	14
117	Godrej Expert Rich Creme Hair Colour Dark Brown (4.06) (MRP-30)	godrej-expert-rich-creme-hair-colour-dark-brown-406-mrp-30	Godrej Expert Rich Creme Hair Colour Dark Brown (4.06) (MRP-30)	Godrej Expert Rich Creme Hair Colour Dark Brown (4.06) (MRP-30)	HRCPCRGEX00000003	GF00055	8.90E+12	6	192	2019-01-08 14:12:06.64524+00	2019-01-08 14:12:06.66165+00	t	14
118	Godrej Expert Rich Creme Hair Colour Natural Black (1.00) (MRP-30)	godrej-expert-rich-creme-hair-colour-natural-black-100-mrp-30	Godrej Expert Rich Creme Hair Colour Natural Black (1.00) (MRP-30)	Godrej Expert Rich Creme Hair Colour Natural Black (1.00) (MRP-30)	HRCPCRGEX00000004	GF00056	8.90E+12	6	192	2019-01-08 14:12:06.676801+00	2019-01-08 14:12:06.695783+00	t	14
119	Ezee Detergent Liquid 250gm (MRP-49)	ezee-detergent-liquid-250gm-mrp-49	Ezee Detergent Liquid 250gm (MRP-49)	Ezee Detergent Liquid 250gm (MRP-49)	DETHLDEZE00000001	GF00059	8.90E+12	4	60	2019-01-08 14:12:06.717498+00	2019-01-08 14:12:06.736345+00	t	71
120	Ezee Detergent Liquid 500gm (MRP-90)	ezee-detergent-liquid-500gm-mrp-90	Ezee Detergent Liquid 500gm (MRP-90)	Ezee Detergent Liquid 500gm (MRP-90)	DETHLDEZE00000002	GF00060_1		6	24	2019-01-08 14:12:06.751962+00	2019-01-08 14:12:06.768391+00	t	71
121	Godrej Ezee MRP-10	godrej-ezee-mrp-10	Godrej Ezee MRP-10	Godrej Ezee MRP-10	DETHLDEZE00000003	GF01691		12	216	2019-01-08 14:12:06.783671+00	2019-01-08 14:12:06.799827+00	t	71
122	Godrej No.1 Coconut and Neem Soap, 100g (Pack of 4) (MRP-68)	godrej-no1-coconut-and-neem-soap-100g-pack-of-4-mrp-68	Godrej No.1 Coconut and Neem Soap, 100g (Pack of 4) (MRP-68)	Godrej No.1 Coconut and Neem Soap, 100g (Pack of 4) (MRP-68)	BBSPCRGNO00000001	GF00066		3	36	2019-01-08 14:12:06.815426+00	2019-01-08 14:12:06.832105+00	t	15
123	Godrej No.1 Sandal & Turmeric Soap 100gm PO4 (MRP-64)	godrej-no1-sandal-turmeric-soap-100gm-po4-mrp-64	Godrej No.1 Sandal & Turmeric Soap 100gm PO4 (MRP-64)	Godrej No.1 Sandal & Turmeric Soap 100gm PO4 (MRP-64)	BBSPCRGNO00000002	GF00062_1		3	36	2019-01-08 14:12:06.847316+00	2019-01-08 14:12:06.864894+00	t	15
124	Godrej No.1 Rosewater and Almonds Soap, 100g (Pack of 4) (MRP-64)	godrej-no1-rosewater-and-almonds-soap-100g-pack-of-4-mrp-64	Godrej No.1 Rosewater and Almonds Soap, 100g (Pack of 4) (MRP-64)	Godrej No.1 Rosewater and Almonds Soap, 100g (Pack of 4) (MRP-64)	BBSPCRGNO00000003	GF00061_1		3	36	2019-01-08 14:12:06.880075+00	2019-01-08 14:12:06.896336+00	t	15
125	Godrej No.1 Lime and Aloe Vera Soap, 100g (Pack of 4) (MRP-60)	godrej-no1-lime-and-aloe-vera-soap-100g-pack-of-4-mrp-60	Godrej No.1 Lime and Aloe Vera Soap, 100g (Pack of 4) (MRP-60)	Godrej No.1 Lime and Aloe Vera Soap, 100g (Pack of 4) (MRP-60)	BBSPCRGNO00000004	GF00063_1		3	36	2019-01-08 14:12:06.912386+00	2019-01-08 14:12:06.928709+00	t	15
126	Godrej No.1 Jasmine Soap, 100g (Pack of 4) (MRP-64)	godrej-no1-jasmine-soap-100g-pack-of-4-mrp-64	Godrej No.1 Jasmine Soap, 100g (Pack of 4) (MRP-64)	Godrej No.1 Jasmine Soap, 100g (Pack of 4) (MRP-64)	BBSPCRGNO00000005	GF00064_1		3	36	2019-01-08 14:12:06.943881+00	2019-01-08 14:12:06.960289+00	t	15
127	Godrej No.1 Aloe Vera and White Lily Soap, 100g (Pack of 4) (MRP-64)	godrej-no1-aloe-vera-and-white-lily-soap-100g-pack-of-4-mrp-64	Godrej No.1 Aloe Vera and White Lily Soap, 100g (Pack of 4) (MRP-64)	Godrej No.1 Aloe Vera and White Lily Soap, 100g (Pack of 4) (MRP-64)	BBSPCRGNO00000006	GF00065_1		3	36	2019-01-08 14:12:06.975979+00	2019-01-08 14:12:06.99237+00	t	15
128	Godrej No.1 Saffron and Milk Cream Soap, 100g (Pack of 4) (MRP-64)	godrej-no1-saffron-and-milk-cream-soap-100g-pack-of-4-mrp-64	Godrej No.1 Saffron and Milk Cream Soap, 100g (Pack of 4) (MRP-64)	Godrej No.1 Saffron and Milk Cream Soap, 100g (Pack of 4) (MRP-64)	BBSPCRGNO00000007	GF00067_1		3	36	2019-01-08 14:12:07.007661+00	2019-01-08 14:12:07.024465+00	t	15
129	Godrej No.1 Lavender and Milk Cream Soap, 100g (Pack of 4) (MRP-64)	godrej-no1-lavender-and-milk-cream-soap-100g-pack-of-4-mrp-64	Godrej No.1 Lavender and Milk Cream Soap, 100g (Pack of 4) (MRP-64)	Godrej No.1 Lavender and Milk Cream Soap, 100g (Pack of 4) (MRP-64)	BBSPCRGNO00000008	GF00068_1		3	36	2019-01-08 14:12:07.039646+00	2019-01-08 14:12:07.056351+00	t	15
130	Godrej No.1 Rosewater and Almonds Soap, 100g (Pack of 4) (MRP-68)	godrej-no1-rosewater-and-almonds-soap-100g-pack-of-4-mrp-68	Godrej No.1 Rosewater and Almonds Soap, 100g (Pack of 4) (MRP-68)	Godrej No.1 Rosewater and Almonds Soap, 100g (Pack of 4) (MRP-68)	BBSPCRGNO00000009	GF00061	8.90E+12	3	36	2019-01-08 14:12:07.071523+00	2019-01-08 14:12:07.088134+00	t	15
131	Godrej No.1 Sandal & Turmeric Soap 100gm PO4	godrej-no1-sandal-turmeric-soap-100gm-po4	#N/A	#N/A	BBSPCRGNO00000010	GF00062	8.90E+12	3	36	2019-01-08 14:12:07.103077+00	2019-01-08 14:12:07.120305+00	t	15
132	Godrej No.1 Lime and Aloe Vera Soap, 100g (Pack of 4) (MRP-68)	godrej-no1-lime-and-aloe-vera-soap-100g-pack-of-4-mrp-68	Godrej No.1 Lime and Aloe Vera Soap, 100g (Pack of 4) (MRP-68)	Godrej No.1 Lime and Aloe Vera Soap, 100g (Pack of 4) (MRP-68)	BBSPCRGNO00000011	GF00063	8.90E+12	3	36	2019-01-08 14:12:07.135392+00	2019-01-08 14:12:07.152126+00	t	15
133	Godrej No.1 Aloe Vera and White Lily Soap, 100g (Pack of 4) (MRP-68)	godrej-no1-aloe-vera-and-white-lily-soap-100g-pack-of-4-mrp-68	Godrej No.1 Aloe Vera and White Lily Soap, 100g (Pack of 4) (MRP-68)	Godrej No.1 Aloe Vera and White Lily Soap, 100g (Pack of 4) (MRP-68)	BBSPCRGNO00000012	GF00065	8.90E+12	3	36	2019-01-08 14:12:07.167168+00	2019-01-08 14:12:07.183746+00	t	15
160	Lizol Disinfectant Floor Cleaner Lavender, 975 ml(MRP-172)	lizol-disinfectant-floor-cleaner-lavender-975-mlmrp-172	Lizol Disinfectant Floor Cleaner Lavender, 975 ml(MRP-172)	Lizol Disinfectant Floor Cleaner Lavender, 975 ml(MRP-172)	BTCHLDLIZ00000006	GF00686_1	8.90E+12	2	12	2019-01-08 14:12:08.039499+00	2019-01-08 14:12:08.056141+00	t	31
134	Godrej No.1 Saffron and Milk Cream Soap, 100g (Pack of 4) (MRP-68)	godrej-no1-saffron-and-milk-cream-soap-100g-pack-of-4-mrp-68	Godrej No.1 Saffron and Milk Cream Soap, 100g (Pack of 4) (MRP-68)	Godrej No.1 Saffron and Milk Cream Soap, 100g (Pack of 4) (MRP-68)	BBSPCRGNO00000013	GF00067	8.90E+12	3	36	2019-01-08 14:12:07.199049+00	2019-01-08 14:12:07.217043+00	t	15
272	EVERYDAY Dairy Whitner Powder 20g	everyday-dairy-whitner-powder-20g	EVERYDAY Dairy Whitner Powder 20g	EVERYDAY Dairy Whitner Powder 20g	PWMDAYEVD00000001	GF01529	8.90106E+12	12	288	2019-01-09 04:45:22.658368+00	2019-01-09 04:45:22.675045+00	t	36
135	Godrej No.1 Lavender and Milk Cream Soap, 100g (Pack of 4) (MRP-68)	godrej-no1-lavender-and-milk-cream-soap-100g-pack-of-4-mrp-68	Godrej No.1 Lavender and Milk Cream Soap, 100g (Pack of 4) (MRP-68)	Godrej No.1 Lavender and Milk Cream Soap, 100g (Pack of 4) (MRP-68)	BBSPCRGNO00000014	GF00068	8.90E+12	3	36	2019-01-08 14:12:07.23244+00	2019-01-08 14:12:07.249262+00	t	15
136	Godrej No.1 Jasmine - 70gm PO4 (MRP-40)	godrej-no1-jasmine-70gm-po4-mrp-40	Godrej No.1 Jasmine - 70gm PO4 (MRP-40)	Godrej No.1 Jasmine - 70gm PO4 (MRP-40)	BBSPCRGNO00000015	GF00069	8.90E+12	6	54	2019-01-08 14:12:07.264984+00	2019-01-08 14:12:07.281534+00	t	15
137	Godrej No.1 Lime & Aloe Vera 70g - PO4 (MRP-40)	godrej-no1-lime-aloe-vera-70g-po4-mrp-40	Godrej No.1 Lime & Aloe Vera 70g - PO4 (MRP-40)	Godrej No.1 Lime & Aloe Vera 70g - PO4 (MRP-40)	BBSPCRGNO00000016	GF00070	8.90E+12	6	54	2019-01-08 14:12:07.296135+00	2019-01-08 14:12:07.312883+00	t	15
138	Godrej No.1 Sandal &Turmeric - 70g PO4 (MRP-40)	godrej-no1-sandal-turmeric-70g-po4-mrp-40	Godrej No.1 Sandal &Turmeric - 70g PO4 (MRP-40)	Godrej No.1 Sandal &Turmeric - 70g PO4 (MRP-40)	BBSPCRGNO00000017	GF00071	8.90E+12	6	54	2019-01-08 14:12:07.329272+00	2019-01-08 14:12:07.345381+00	t	15
139	Godrej Nupur Mehendi 25gm (MRP-15)	godrej-nupur-mehendi-25gm-mrp-15	Godrej Nupur Mehendi 25gm (MRP-15)	Godrej Nupur Mehendi 25gm (MRP-15)	HRCPCRGNU00000001	GF00073	8.90E+12	12	324	2019-01-08 14:12:07.361332+00	2019-01-08 14:12:07.377893+00	t	16
140	Godrej Nupur Mehendi 50gm (MRP-35)	godrej-nupur-mehendi-50gm-mrp-35	Godrej Nupur Mehendi 50gm (MRP-35)	Godrej Nupur Mehendi 50gm (MRP-35)	HRCPCRGNU00000002	GF00075		6	180	2019-01-08 14:12:07.393199+00	2019-01-08 14:12:07.409432+00	t	16
141	Godrej Nupur Mehendi 50gm (MRP-35)	godrej-nupur-mehendi-50gm-mrp-35	Godrej Nupur Mehendi 50gm (MRP-35)	Godrej Nupur Mehendi 50gm (MRP-35)	HRCPCRGNU00000003	GF00075_N		3	180	2019-01-08 14:12:07.424632+00	2019-01-08 14:12:07.442321+00	t	16
142	Good knight Advanced Fast Card (MRP-10)	good-knight-advanced-fast-card-mrp-10	Good knight Advanced Fast Card (MRP-10)	Good knight Advanced Fast Card (MRP-10)	MQRHLDGGN00000001	GF00082	8.90E+12	12	480	2019-01-08 14:12:07.45786+00	2019-01-08 14:12:07.47381+00	t	17
143	Hair & Care Fruit Oils Green, 200 ml(MRP-115)	hair-care-fruit-oils-green-200-mlmrp-115	Hair & Care Fruit Oils Green, 200 ml(MRP-115)	Hair & Care Fruit Oils Green, 200 ml(MRP-115)	HRCPCRHNC00000001	GF00138_1	8.90E+12	3	72	2019-01-08 14:12:07.489021+00	2019-01-08 14:12:07.505678+00	t	70
144	Hair & Care Fruit Oils Green, 100 ml(MRP-60)	hair-care-fruit-oils-green-100-mlmrp-60	Hair & Care Fruit Oils Green, 100 ml(MRP-60)	Hair & Care Fruit Oils Green, 100 ml(MRP-60)	HRCPCRHNC00000002	GF00137	89002827	6	144	2019-01-08 14:12:07.521758+00	2019-01-08 14:12:07.538775+00	t	70
145	Hair & Care Fruit Oils Green, 50 ml(MRP-32)	hair-care-fruit-oils-green-50-mlmrp-32	Hair & Care Fruit Oils Green, 50 ml(MRP-32)	Hair & Care Fruit Oils Green, 50 ml(MRP-32)	HRCPCRHNC00000003	GF00140_1	89002797	6	288	2019-01-08 14:12:07.554346+00	2019-01-08 14:12:07.570834+00	t	70
146	H&S Shampoo Anti Hair Fall 8.5ml  4+1 Offer (MRP-4) Pack of 20	hs-shampoo-anti-hair-fall-85ml-41-offer-mrp-4-pack-of-20	H&S Shampoo Anti Hair Fall 8.5ml  4+1 Offer (MRP-4) Pack of 20	H&S Shampoo Anti Hair Fall 8.5ml  4+1 Offer (MRP-4) Pack of 20	HRCPCRHNS00000001	GF01027	4.90E+12	1	40	2019-01-08 14:12:07.586914+00	2019-01-08 14:12:07.60342+00	t	69
147	H&S Shampoo Cool Menthol 8.5ml  4+1 Offer (MRP-4) Pack of 20	hs-shampoo-cool-menthol-85ml-41-offer-mrp-4-pack-of-20	H&S Shampoo Cool Menthol 8.5ml  4+1 Offer (MRP-4) Pack of 20	H&S Shampoo Cool Menthol 8.5ml  4+1 Offer (MRP-4) Pack of 20	HRCPCRHNS00000002	GF01028	4.90E+12	1	40	2019-01-08 14:12:07.618947+00	2019-01-08 14:12:07.635863+00	t	69
148	H&S Shampoo Lemon Fresh 8.5 ml(MRP-4)  Pack-16	hs-shampoo-lemon-fresh-85-mlmrp-4-pack-16	H&S Shampoo Lemon Fresh 8.5 ml(MRP-4)  Pack-16	H&S Shampoo Lemon Fresh 8.5 ml(MRP-4)  Pack-16	HRCPCRHNS00000003	GF01029	4.90E+12	1	40	2019-01-08 14:12:07.651482+00	2019-01-08 14:12:07.667841+00	t	69
149	H&S Shampoo Silky Black 8.5ml  4+1 Offer (MRP-4) Pack of 20	hs-shampoo-silky-black-85ml-41-offer-mrp-4-pack-of-20	H&S Shampoo Silky Black 8.5ml  4+1 Offer (MRP-4) Pack of 20	H&S Shampoo Silky Black 8.5ml  4+1 Offer (MRP-4) Pack of 20	HRCPCRHNS00000004	GF01030	4.90E+12	1	40	2019-01-08 14:12:07.683945+00	2019-01-08 14:12:07.700597+00	t	69
150	H&S Shampoo Smooth & Silky  8.5ml  4+1 Offer (MRP-4) Pack of 20	hs-shampoo-smooth-silky-85ml-41-offer-mrp-4-pack-of-20	H&S Shampoo Smooth & Silky  8.5ml  4+1 Offer (MRP-4) Pack of 20	H&S Shampoo Smooth & Silky  8.5ml  4+1 Offer (MRP-4) Pack of 20	HRCPCRHNS00000005	GF01031	4.90E+12	1	40	2019-01-08 14:12:07.715766+00	2019-01-08 14:12:07.732025+00	t	69
151	HERBO WASH DETERGENT POWDER 1 KG(MRP-70)	herbo-wash-detergent-powder-1-kgmrp-70	HERBO WASH DETERGENT POWDER 1 KG(MRP-70)	HERBO WASH DETERGENT POWDER 1 KG(MRP-70)	DETHLDHER00000001	GF01437		5	25	2019-01-08 14:12:07.74729+00	2019-01-08 14:12:07.763571+00	t	68
152	HERBO WASH DETERGENT POWDER 500 GM(MRP-35)	herbo-wash-detergent-powder-500-gmmrp-35	HERBO WASH DETERGENT POWDER 500 GM(MRP-35)	HERBO WASH DETERGENT POWDER 500 GM(MRP-35)	DETHLDHER00000002	GF01435		4	40	2019-01-08 14:12:07.77989+00	2019-01-08 14:12:07.796901+00	t	68
153	Lal Dant Manjan 100gm(MRP-43)	lal-dant-manjan-100gmmrp-43	Lal Dant Manjan 100gm(MRP-43)	Lal Dant Manjan 100gm(MRP-43)	ORCPCRRED00000001	GF01644	8.90E+12	4	80	2019-01-08 14:12:07.812442+00	2019-01-08 14:12:07.828813+00	t	67
154	LIFEBUOY TOTAL SOAP 62G(MRP-10)	lifebuoy-total-soap-62gmrp-10	LIFEBUOY TOTAL SOAP 62G(MRP-10)	LIFEBUOY TOTAL SOAP 62G(MRP-10)	BBSPCRLIF00000001	GF01185	8.90E+12	12	144	2019-01-08 14:12:07.843708+00	2019-01-08 14:12:07.860377+00	t	20
155	Lizol Flr Jasmine- 975ml wth Free Hrpic - 200 ml (MRP-172)	lizol-flr-jasmine-975ml-wth-free-hrpic-200-ml-mrp-172	Lizol Flr Jasmine- 975ml wth Free Hrpic - 200 ml (MRP-172)	Lizol Flr Jasmine- 975ml wth Free Hrpic - 200 ml (MRP-172)	BTCHLDLIZ00000001	GF00641	8.90E+12	2	8	2019-01-08 14:12:07.877096+00	2019-01-08 14:12:07.893511+00	t	31
156	Lizol Disinfectant Floor Cleaner Citrus, 500 ml(MRP-89)	lizol-disinfectant-floor-cleaner-citrus-500-mlmrp-89	Lizol Disinfectant Floor Cleaner Citrus, 500 ml(MRP-89)	Lizol Disinfectant Floor Cleaner Citrus, 500 ml(MRP-89)	BTCHLDLIZ00000002	GF00693	8.90E+12	3	24	2019-01-08 14:12:07.908464+00	2019-01-08 14:12:07.925225+00	t	31
157	Lizol Floral- 975 ml with Free Harpic 200 ml (MRP-172)	lizol-floral-975-ml-with-free-harpic-200-ml-mrp-172	Lizol Floral- 975 ml with Free Harpic 200 ml (MRP-172)	Lizol Floral- 975 ml with Free Harpic 200 ml (MRP-172)	BTCHLDLIZ00000003	GF00702	8.90E+12	2	8	2019-01-08 14:12:07.940605+00	2019-01-08 14:12:07.956953+00	t	31
158	Lizol Disinfectant Floor Cleaner Jasmine, 500 ml(MRP-89)	lizol-disinfectant-floor-cleaner-jasmine-500-mlmrp-89	Lizol Disinfectant Floor Cleaner Jasmine, 500 ml(MRP-89)	Lizol Disinfectant Floor Cleaner Jasmine, 500 ml(MRP-89)	BTCHLDLIZ00000004	GF00638_1	8.90E+12	3	24	2019-01-08 14:12:07.971945+00	2019-01-08 14:12:07.988226+00	t	31
159	Lizol Disinfectant Floor Cleaner Lavender, 500ml(MRP-89)	lizol-disinfectant-floor-cleaner-lavender-500mlmrp-89	Lizol Disinfectant Floor Cleaner Lavender, 500ml(MRP-89)	Lizol Disinfectant Floor Cleaner Lavender, 500ml(MRP-89)	BTCHLDLIZ00000005	GF00688_1	8.90E+12	3	24	2019-01-08 14:12:08.005801+00	2019-01-08 14:12:08.022719+00	t	31
161	Lizol Disinfectant Floor Cleaner Pine, 2 L(MRP-344)	lizol-disinfectant-floor-cleaner-pine-2-lmrp-344	Lizol Disinfectant Floor Cleaner Pine, 2 L(MRP-344)	Lizol Disinfectant Floor Cleaner Pine, 2 L(MRP-344)	BTCHLDLIZ00000007	GF00703_1	8.90E+12	1	6	2019-01-08 14:12:08.071865+00	2019-01-08 14:12:08.088905+00	t	31
381	Tide Laundary Powder Jasmine & Rose 110gm(MRP-10) Pack-12	tide-laundary-powder-jasmine-rose-110gmmrp-10-pack-12	Tide Laundary Powder Jasmine & Rose 110gm(MRP-10) Pack-12	Tide Laundary Powder Jasmine & Rose 110gm(MRP-10) Pack-12	DETHLDTID00000005	GF01047		1	5	2019-01-09 09:44:04.317256+00	2019-01-09 09:44:04.335434+00	t	81
162	Lizol Disinfectant Surface Cleaner Jasmine, 2 L(MRP-344)	lizol-disinfectant-surface-cleaner-jasmine-2-lmrp-344	Lizol Disinfectant Surface Cleaner Jasmine, 2 L(MRP-344)	Lizol Disinfectant Surface Cleaner Jasmine, 2 L(MRP-344)	BTCHLDLIZ00000008	GF00642_1	8.90E+12	1	6	2019-01-08 14:12:08.105205+00	2019-01-08 14:12:08.122313+00	t	31
163	Lizol Disinfectant Floor Cleaner Pine, 500 ml(MRP-89)	lizol-disinfectant-floor-cleaner-pine-500-mlmrp-89	Lizol Disinfectant Floor Cleaner Pine, 500 ml(MRP-89)	Lizol Disinfectant Floor Cleaner Pine, 500 ml(MRP-89)	BTCHLDLIZ00000009	GF00680_1	8.90E+12	3	24	2019-01-08 14:12:08.138465+00	2019-01-08 14:12:08.155582+00	t	31
164	Lizol Disinfectant Floor Cleaner Jasmine, 975 ml(MRP-172)	lizol-disinfectant-floor-cleaner-jasmine-975-mlmrp-172	Lizol Disinfectant Floor Cleaner Jasmine, 975 ml(MRP-172)	Lizol Disinfectant Floor Cleaner Jasmine, 975 ml(MRP-172)	BTCHLDLIZ00000010	GF00640_1	8.90E+12	2	12	2019-01-08 14:12:08.171474+00	2019-01-08 14:12:08.187772+00	t	31
165	Lizol Disinfectant Floor Cleaner Citrus, 200 ml(MRP-36)	lizol-disinfectant-floor-cleaner-citrus-200-mlmrp-36	Lizol Disinfectant Floor Cleaner Citrus, 200 ml(MRP-36)	Lizol Disinfectant Floor Cleaner Citrus, 200 ml(MRP-36)	BTCHLDLIZ00000011	GF00682	8.90E+12	6	48	2019-01-08 14:12:08.2043+00	2019-01-08 14:12:08.221131+00	t	31
166	Lizol Disinfectant Floor Cleaner Floral, 200ml(MRP-36)	lizol-disinfectant-floor-cleaner-floral-200mlmrp-36	Lizol Disinfectant Floor Cleaner Floral, 200ml(MRP-36)	Lizol Disinfectant Floor Cleaner Floral, 200ml(MRP-36)	BTCHLDLIZ00000012	GF00683	8.90E+12	6	48	2019-01-08 14:12:08.236744+00	2019-01-08 14:12:08.254066+00	t	31
167	Lizol Disinfectant Surface Cleaner Citrus 975ml(MRP-172)	lizol-disinfectant-surface-cleaner-citrus-975mlmrp-172	Lizol Disinfectant Surface Cleaner Citrus 975ml(MRP-172)	Lizol Disinfectant Surface Cleaner Citrus 975ml(MRP-172)	BTCHLDLIZ00000013	GF00691_1	8.90E+12	2	12	2019-01-08 14:12:08.270272+00	2019-01-08 14:12:08.286739+00	t	31
168	Lizol Disinfectant Floor Cleaner Sandal, 500 ml(MRP-89)	lizol-disinfectant-floor-cleaner-sandal-500-mlmrp-89	Lizol Disinfectant Floor Cleaner Sandal, 500 ml(MRP-89)	Lizol Disinfectant Floor Cleaner Sandal, 500 ml(MRP-89)	BTCHLDLIZ00000014	GF00645_1	8.90E+12	3	24	2019-01-08 14:12:08.302583+00	2019-01-08 14:12:08.318719+00	t	31
169	LUX FRSH SPLASH SOAP 54GM(MRP-10)	lux-frsh-splash-soap-54gmmrp-10	LUX FRSH SPLASH SOAP 54GM(MRP-10)	LUX FRSH SPLASH SOAP 54GM(MRP-10)	BBSPCRLUX00000001	GF01186	8.90E+12	12	144	2019-01-08 14:12:08.334885+00	2019-01-08 14:12:08.35289+00	t	21
170	LUX SOFT TOUCH SOAP 3X100G(MRP-73)	lux-soft-touch-soap-3x100gmrp-73	LUX SOFT TOUCH SOAP 3X100G(MRP-73)	LUX SOFT TOUCH SOAP 3X100G(MRP-73)	BBSPCRLUX00000002	GF01196	8.90E+12	1	36	2019-01-08 14:12:08.368638+00	2019-01-08 14:12:08.385837+00	t	21
171	Dabur Meswak Toothpaste - 100 g (MRP-50)	dabur-meswak-toothpaste-100-g-mrp-50	Dabur Meswak Toothpaste - 100 g (MRP-50)	Dabur Meswak Toothpaste - 100 g (MRP-50)	ORCPCRDME00000001	GF01645	8.90E+12	3	72	2019-01-08 14:12:08.400978+00	2019-01-08 14:12:08.417525+00	t	11
172	Moov Crm Reg 5gm(MRP-10)	moov-crm-reg-5gmmrp-10	Moov Crm Reg 5gm(MRP-10)	Moov Crm Reg 5gm(MRP-10)	EVMPCRMOV00000001	GF01002	8.90E+12	12	480	2019-01-08 14:12:08.432323+00	2019-01-08 14:12:08.448561+00	t	32
173	Moov Ortho Knee and Joints Pain Relief Cream - 50 gm(MRP-145)	moov-ortho-knee-and-joints-pain-relief-cream-50-gmmrp-145	Moov Ortho Knee and Joints Pain Relief Cream - 50 gm(MRP-145)	Moov Ortho Knee and Joints Pain Relief Cream - 50 gm(MRP-145)	EVMPCRMOV00000002	GF01003		1	144	2019-01-08 14:12:08.464873+00	2019-01-08 14:12:08.488388+00	t	32
174	Moov Ortho Knee and Joints Pain Relief Cream - 15 g(MRP-65)	moov-ortho-knee-and-joints-pain-relief-cream-15-gmrp-65	Moov Ortho Knee and Joints Pain Relief Cream - 15 g(MRP-65)	Moov Ortho Knee and Joints Pain Relief Cream - 15 g(MRP-65)	EVMPCRMOV00000003	GF00715_1	8.90E+12	3	240	2019-01-08 14:12:08.504403+00	2019-01-08 14:12:08.521342+00	t	32
175	MOOV CRM REG 15GM-NEW PK(MRP-66)	moov-crm-reg-15gm-new-pkmrp-66	MOOV CRM REG 15GM-NEW PK(MRP-66)	MOOV CRM REG 15GM-NEW PK(MRP-66)	EVMPCRMOV00000004	GF00728_1	8.90E+12	12	240	2019-01-08 14:12:08.537223+00	2019-01-08 14:12:08.554393+00	t	32
176	Nihar Naturals Shanti Amla Badam Hair Oil, 80 ml(MRP-20)	nihar-naturals-shanti-amla-badam-hair-oil-80-mlmrp-20	Nihar Naturals Shanti Amla Badam Hair Oil, 80 ml(MRP-20)	Nihar Naturals Shanti Amla Badam Hair Oil, 80 ml(MRP-20)	HRCPCRNIH00000001	GF00156	89006306	6	144	2019-01-08 14:12:08.571308+00	2019-01-08 14:12:08.588195+00	t	27
177	Nihar Naturals Shanti Amla Badam Hair Oil, 300 ml (MRP-88)	nihar-naturals-shanti-amla-badam-hair-oil-300-ml-mrp-88	Nihar Naturals Shanti Amla Badam Hair Oil, 300 ml (MRP-88)	Nihar Naturals Shanti Amla Badam Hair Oil, 300 ml (MRP-88)	HRCPCRNIH00000002	GF00154_1	8.90E+12	3	36	2019-01-08 14:12:08.604996+00	2019-01-08 14:12:08.622391+00	t	27
178	NIP DISHWASH BAR  140GM X 4(MRP-30)	nip-dishwash-bar-140gm-x-4mrp-30	NIP DISHWASH BAR  140GM X 4(MRP-30)	NIP DISHWASH BAR  140GM X 4(MRP-30)	DWSHLDFNI00000001	GF01125	8.90E+12	4	24	2019-01-08 14:12:08.638063+00	2019-01-08 14:12:08.65615+00	t	13
179	NIP DISHWASH BAR  300GM X 3(MRP-46)	nip-dishwash-bar-300gm-x-3mrp-46	NIP DISHWASH BAR  300GM X 3(MRP-46)	NIP DISHWASH BAR  300GM X 3(MRP-46)	DWSHLDFNI00000002	GF01126	8.90E+12	4	20	2019-01-08 14:12:08.671727+00	2019-01-08 14:12:08.688408+00	t	13
180	Odonil Air fresherner Jasmine - 50 g (MRP-46)	odonil-air-fresherner-jasmine-50-g-mrp-46	Odonil Air fresherner Jasmine - 50 g (MRP-46)	Odonil Air fresherner Jasmine - 50 g (MRP-46)	FRSHLDDOD00000001	GF01638	8.90E+12	6	144	2019-01-08 14:12:08.704609+00	2019-01-08 14:12:08.721514+00	t	12
181	Odonil Block - 50 g (Lavender)(MRP-46)	odonil-block-50-g-lavendermrp-46	Odonil Block - 50 g (Lavender)(MRP-46)	Odonil Block - 50 g (Lavender)(MRP-46)	FRSHLDDOD00000002	GF01639	8.90E+12	6	144	2019-01-08 14:12:08.73727+00	2019-01-08 14:12:08.753461+00	t	12
182	Odonil Block - 50 g (Rose) (MRP-46)	odonil-block-50-g-rose-mrp-46	Odonil Block - 50 g (Rose) (MRP-46)	Odonil Block - 50 g (Rose) (MRP-46)	FRSHLDDOD00000003	GF01640	8.90E+12	6	144	2019-01-08 14:12:08.768914+00	2019-01-08 14:12:08.785339+00	t	12
183	Odonil Zipper Pack - 10 g (Lavendar)(MRP-50)	odonil-zipper-pack-10-g-lavendarmrp-50	Odonil Zipper Pack - 10 g (Lavendar)(MRP-50)	Odonil Zipper Pack - 10 g (Lavendar)(MRP-50)	FRSHLDDOD00000004	GF01641	8.90E+12	6	120	2019-01-08 14:12:08.800087+00	2019-01-08 14:12:08.816159+00	t	12
184	Odonil Zipper Pack - 10 g (Citrus)(MRP-50)	odonil-zipper-pack-10-g-citrusmrp-50	Odonil Zipper Pack - 10 g (Citrus)(MRP-50)	Odonil Zipper Pack - 10 g (Citrus)(MRP-50)	FRSHLDDOD00000005	GF01642	8.90E+12	6	120	2019-01-08 14:12:08.833763+00	2019-01-08 14:12:08.850347+00	t	12
185	Odonil Zipper Pack - 10 g (Jasmine)(MRP-50)	odonil-zipper-pack-10-g-jasminemrp-50	Odonil Zipper Pack - 10 g (Jasmine)(MRP-50)	Odonil Zipper Pack - 10 g (Jasmine)(MRP-50)	FRSHLDDOD00000006	GF01643	8.90E+12	6	120	2019-01-08 14:12:08.865473+00	2019-01-08 14:12:08.882022+00	t	12
186	Pampers Pants Small 2pc  New Baby (MRP-16)	pampers-pants-small-2pc-new-baby-mrp-16	Pampers Pants Small 2pc  New Baby (MRP-16)	Pampers Pants Small 2pc  New Baby (MRP-16)	BBCPCRPAM00000001	GF01034	4.90E+12	6	96	2019-01-08 14:12:08.897415+00	2019-01-08 14:12:08.913908+00	t	79
187	Pampers Pants Small 4pc (MRP-40)	pampers-pants-small-4pc-mrp-40	Pampers Pants Small 4pc (MRP-40)	Pampers Pants Small 4pc (MRP-40)	BBCPCRPAM00000002	GF01035	4.90E+12	3	48	2019-01-08 14:12:08.92955+00	2019-01-08 14:12:08.945891+00	t	79
188	Pampers baby diapers 2pcs New baby (MRP-24)	pampers-baby-diapers-2pcs-new-baby-mrp-24	Pampers baby diapers 2pcs New baby (MRP-24)	Pampers baby diapers 2pcs New baby (MRP-24)	BBCPCRPAM00000003	GF01040	4.90E+12	6	108	2019-01-08 14:12:08.962456+00	2019-01-08 14:12:08.978423+00	t	79
273	CERELAC STAGE 3, wheat rice and mixed fruit 300g	cerelac-stage-3-wheat-rice-and-mixed-fruit-300g	CERELAC STAGE 3, wheat rice and mixed fruit 300g	CERELAC STAGE 3, wheat rice and mixed fruit 300g	BBFINFCER00000001	GF01530	8.90106E+12	1	24	2019-01-09 04:45:22.694528+00	2019-01-09 04:45:22.710452+00	t	37
189	Pampers Pants small 2pc (MRP-20)	pampers-pants-small-2pc-mrp-20	Pampers Pants small 2pc (MRP-20)	Pampers Pants small 2pc (MRP-20)	BBCPCRPAM00000004	GF01041	4.90E+12	6	96	2019-01-08 14:12:08.994791+00	2019-01-08 14:12:09.012334+00	t	79
190	Pampers Pants Large 2Pc (MRP-28)	pampers-pants-large-2pc-mrp-28	Pampers Pants Large 2Pc (MRP-28)	Pampers Pants Large 2Pc (MRP-28)	BBCPCRPAM00000005	GF01033	4.90E+12	6	96	2019-01-08 14:12:09.029467+00	2019-01-08 14:12:09.046812+00	t	79
191	Pantene Shampoo Lively Clean 8.5ml(MRP-4) pack-16	pantene-shampoo-lively-clean-85mlmrp-4-pack-16	Pantene Shampoo Lively Clean 8.5ml(MRP-4) pack-16	Pantene Shampoo Lively Clean 8.5ml(MRP-4) pack-16	HRCPCRPAN00000001	GF01036	4.90E+12	1	40	2019-01-08 14:12:09.062112+00	2019-01-08 14:12:09.078806+00	t	66
192	Pantene Shampoo Long Black 8.5ml(MRP-4) pack-16	pantene-shampoo-long-black-85mlmrp-4-pack-16	Pantene Shampoo Long Black 8.5ml(MRP-4) pack-16	Pantene Shampoo Long Black 8.5ml(MRP-4) pack-16	HRCPCRPAN00000002	GF01037	4.90E+12	1	40	2019-01-08 14:12:09.094321+00	2019-01-08 14:12:09.111858+00	t	66
193	Pantene Shampoo Total Damage Care 8.5ml(MRP-4) pack-16	pantene-shampoo-total-damage-care-85mlmrp-4-pack-16	Pantene Shampoo Total Damage Care 8.5ml(MRP-4) pack-16	Pantene Shampoo Total Damage Care 8.5ml(MRP-4) pack-16	HRCPCRPAN00000003	GF01038	4.90E+12	1	40	2019-01-08 14:12:09.128642+00	2019-01-08 14:12:09.145131+00	t	66
194	Pantene Silky Smooth Care 8.5ml(MRP-4) pack-16	pantene-silky-smooth-care-85mlmrp-4-pack-16	Pantene Silky Smooth Care 8.5ml(MRP-4) pack-16	Pantene Silky Smooth Care 8.5ml(MRP-4) pack-16	HRCPCRPAN00000004	GF01039	4.90E+12	1	40	2019-01-08 14:12:09.160838+00	2019-01-08 14:12:09.177492+00	t	66
195	Parachute Advansed Jasmine Coconut Hair Oil, 200 ml(MRP-92)	parachute-advansed-jasmine-coconut-hair-oil-200-mlmrp-92	Parachute Advansed Jasmine Coconut Hair Oil, 200 ml(MRP-92)	Parachute Advansed Jasmine Coconut Hair Oil, 200 ml(MRP-92)	HRCPCRPAR00000001	GF00192	8.90E+12	3	72	2019-01-08 14:12:09.193282+00	2019-01-08 14:12:09.209641+00	t	28
196	Parachute Coconut Oil 50ml- FT(MRP-20)	parachute-coconut-oil-50ml-ftmrp-20	Parachute Coconut Oil 50ml- FT(MRP-20)	Parachute Coconut Oil 50ml- FT(MRP-20)	HRCPCRPAR00000002	GF00198		12	384	2019-01-08 14:12:09.224655+00	2019-01-08 14:12:09.240442+00	t	28
197	Parachute Advansed Jasmine Coconut Hair Oil, 300 ml(MRP-135)	parachute-advansed-jasmine-coconut-hair-oil-300-mlmrp-135	Parachute Advansed Jasmine Coconut Hair Oil, 300 ml(MRP-135)	Parachute Advansed Jasmine Coconut Hair Oil, 300 ml(MRP-135)	HRCPCRPAR00000003	GF00193	8.90E+12	2	36	2019-01-08 14:12:09.255598+00	2019-01-08 14:12:09.272982+00	t	28
198	Parachute Advansed Coconut Hair Oil, 175 ml (MRP-95)	parachute-advansed-coconut-hair-oil-175-ml-mrp-95	Parachute Advansed Coconut Hair Oil, 175 ml (MRP-95)	Parachute Advansed Coconut Hair Oil, 175 ml (MRP-95)	HRCPCRPAR00000004	GF00187	8.90E+12	3	48	2019-01-08 14:12:09.28815+00	2019-01-08 14:12:09.304411+00	t	28
199	Parachute Advansed Coconut Hair Oil - 75 ml Flip Top (MRP-55)	parachute-advansed-coconut-hair-oil-75-ml-flip-top-mrp-55	Parachute Advansed Coconut Hair Oil - 75 ml Flip Top (MRP-55)	Parachute Advansed Coconut Hair Oil - 75 ml Flip Top (MRP-55)	HRCPCRPAR00000005	GF00189_1	8.90E+12	6	96	2019-01-08 14:12:09.319683+00	2019-01-08 14:12:09.336348+00	t	28
200	Parachute Coconut Oil - 300 ml (Easy Jar)(MRP-133)	parachute-coconut-oil-300-ml-easy-jarmrp-133	Parachute Coconut Oil - 300 ml (Easy Jar)(MRP-133)	Parachute Coconut Oil - 300 ml (Easy Jar)(MRP-133)	HRCPCRPAR00000006	GF01517	8.90E+12	1	60	2019-01-08 14:12:09.351402+00	2019-01-08 14:12:09.36809+00	t	28
201	Parachute Coconut Oil - 600 ml (Easy Jar)(MRP-259)	parachute-coconut-oil-600-ml-easy-jarmrp-259	Parachute Coconut Oil - 600 ml (Easy Jar)(MRP-259)	Parachute Coconut Oil - 600 ml (Easy Jar)(MRP-259)	HRCPCRPAR00000007	GF01518	8.90E+12	4	20	2019-01-08 14:12:09.383283+00	2019-01-08 14:12:09.401901+00	t	28
202	Patajnali SUPERIOR DETERGENT CAKE 125 G(MRP-8)	patajnali-superior-detergent-cake-125-gmrp-8	Patajnali SUPERIOR DETERGENT CAKE 125 G(MRP-8)	Patajnali SUPERIOR DETERGENT CAKE 125 G(MRP-8)	DETHLDPAT00000001	GF00363	8.90E+12	10	100	2019-01-08 14:12:09.417222+00	2019-01-08 14:12:09.433643+00	t	54
203	Patajnali ALOEVERA KANTI BODY CLEANSER 150 G(MRP-28)	patajnali-aloevera-kanti-body-cleanser-150-gmrp-28	Patajnali ALOEVERA KANTI BODY CLEANSER 150 G(MRP-28)	Patajnali ALOEVERA KANTI BODY CLEANSER 150 G(MRP-28)	BBSPCRPAT00000001	GF00327	8.90E+12	6	72	2019-01-08 14:12:09.449098+00	2019-01-08 14:12:09.46529+00	t	54
204	Patajnali ALOEVERA KANTI BODY CLEANSER 75 G(MRP-15)	patajnali-aloevera-kanti-body-cleanser-75-gmrp-15	Patajnali ALOEVERA KANTI BODY CLEANSER 75 G(MRP-15)	Patajnali ALOEVERA KANTI BODY CLEANSER 75 G(MRP-15)	BBSPCRPAT00000002	GF00328	8.90E+12	12	144	2019-01-08 14:12:09.480261+00	2019-01-08 14:12:09.496136+00	t	54
205	Patajnali AMLA HAIR OIL 100 ML(MRP-40)	patajnali-amla-hair-oil-100-mlmrp-40	Patajnali AMLA HAIR OIL 100 ML(MRP-40)	Patajnali AMLA HAIR OIL 100 ML(MRP-40)	HRCPCRPAT00000001	GF00332	8.90E+12	6	96	2019-01-08 14:12:09.511492+00	2019-01-08 14:12:09.527426+00	t	54
206	Patajnali POPULAR DETERGENT CAKE 125 G(MRP-6)	patajnali-popular-detergent-cake-125-gmrp-6	Patajnali POPULAR DETERGENT CAKE 125 G(MRP-6)	Patajnali POPULAR DETERGENT CAKE 125 G(MRP-6)	DETHLDPAT00000002	GF00356	8.90E+12	10	100	2019-01-08 14:12:09.542438+00	2019-01-08 14:12:09.560783+00	t	54
207	Patajnali POPULAR DETERGENT CAKE 250 G(MRP-12)	patajnali-popular-detergent-cake-250-gmrp-12	Patajnali POPULAR DETERGENT CAKE 250 G(MRP-12)	Patajnali POPULAR DETERGENT CAKE 250 G(MRP-12)	DETHLDPAT00000003	GF00357	8.90E+12	5	50	2019-01-08 14:12:09.576248+00	2019-01-08 14:12:09.592775+00	t	54
208	Patajnali SUPERIOR DETERGENT CAKE 250 G(MRP-16)	patajnali-superior-detergent-cake-250-gmrp-16	Patajnali SUPERIOR DETERGENT CAKE 250 G(MRP-16)	Patajnali SUPERIOR DETERGENT CAKE 250 G(MRP-16)	DETHLDPAT00000004	GF00364	8.90E+12	5	50	2019-01-08 14:12:09.609199+00	2019-01-08 14:12:09.625469+00	t	54
209	Patajnali DANT KANTI NATURAL TOOTHPASTE 100 G(MRP-40)	patajnali-dant-kanti-natural-toothpaste-100-gmrp-40	Patajnali DANT KANTI NATURAL TOOTHPASTE 100 G(MRP-40)	Patajnali DANT KANTI NATURAL TOOTHPASTE 100 G(MRP-40)	ORCPCRPAT00000001	GF00340	8.90E+12	12	96	2019-01-08 14:12:09.641022+00	2019-01-08 14:12:09.657775+00	t	54
210	Patajnali SUPERIOR DETERGENT POWDER 500 G(MRP-35)	patajnali-superior-detergent-powder-500-gmrp-35	Patajnali SUPERIOR DETERGENT POWDER 500 G(MRP-35)	Patajnali SUPERIOR DETERGENT POWDER 500 G(MRP-35)	DETHLDPAT00000005	GF00368		5	50	2019-01-08 14:12:09.673595+00	2019-01-08 14:12:09.69032+00	t	54
211	Patajnali SAUNDARYA FACE WASH 60 G(MRP-60)	patajnali-saundarya-face-wash-60-gmrp-60	Patajnali SAUNDARYA FACE WASH 60 G(MRP-60)	Patajnali SAUNDARYA FACE WASH 60 G(MRP-60)	SKCPCRPAT00000001	GF00362	8.90E+12	3	96	2019-01-08 14:12:09.706064+00	2019-01-08 14:12:09.723127+00	t	54
212	SAUNDARYA ALOEVERA GEL K.CHANDAN 60ML-T(MRP-50)	saundarya-aloevera-gel-kchandan-60ml-tmrp-50	SAUNDARYA ALOEVERA GEL K.CHANDAN 60ML-T(MRP-50)	SAUNDARYA ALOEVERA GEL K.CHANDAN 60ML-T(MRP-50)	SKCPCRPAT00000002	GF01293	8.90E+12	3	96	2019-01-08 14:12:09.73871+00	2019-01-08 14:12:09.755268+00	t	54
213	PEPSODENT  GERMICHECK CAVITY PROTECTION 25G(MRP-10)	pepsodent-germicheck-cavity-protection-25gmrp-10	PEPSODENT  GERMICHECK CAVITY PROTECTION 25G(MRP-10)	PEPSODENT  GERMICHECK CAVITY PROTECTION 25G(MRP-10)	ORCPCRPEP00000001	GF01188	8.90E+12	12	288	2019-01-08 14:12:09.770157+00	2019-01-08 14:12:09.786453+00	t	65
214	Ponds Moisturising Cold Cream 6gm(MRP-5)	ponds-moisturising-cold-cream-6gmmrp-5	Ponds Moisturising Cold Cream 6gm(MRP-5)	Ponds Moisturising Cold Cream 6gm(MRP-5)	SKCPCRPND00000001	GF01177	NA	64	768	2019-01-08 14:12:09.801811+00	2019-01-08 14:12:09.818374+00	t	22
215	Revive Liquid - 200 gm(MRP-62)	revive-liquid-200-gmmrp-62	Revive Liquid - 200 gm(MRP-62)	Revive Liquid - 200 gm(MRP-62)	DETHLDREV00000001	GF00203	8.90E+12	3	72	2019-01-08 14:12:09.836112+00	2019-01-08 14:12:09.868631+00	t	64
274	LACTOGEN Stage 1 Infant Formula Tin 400g	lactogen-stage-1-infant-formula-tin-400g	LACTOGEN Stage 1 Infant Formula Tin 400g	LACTOGEN Stage 1 Infant Formula Tin 400g	BBFINFLAC00000001	GF01531	8.90106E+12	1	24	2019-01-09 04:45:22.728438+00	2019-01-09 04:45:22.748696+00	t	38
216	Revive Anti Bacterial Instant Starch - 50 gm Sachet(MRP-17)	revive-anti-bacterial-instant-starch-50-gm-sachetmrp-17	Revive Anti Bacterial Instant Starch - 50 gm Sachet(MRP-17)	Revive Anti Bacterial Instant Starch - 50 gm Sachet(MRP-17)	DETHLDREV00000002	GF00201	8.90E+12	10	270	2019-01-08 14:12:09.883845+00	2019-01-08 14:12:09.900631+00	t	64
217	Revive Liquid - 100 gm(MRP-29)	revive-liquid-100-gmmrp-29	Revive Liquid - 100 gm(MRP-29)	Revive Liquid - 100 gm(MRP-29)	DETHLDREV00000003	GF00202	8.90E+12	6	144	2019-01-08 14:12:09.91704+00	2019-01-08 14:12:09.934148+00	t	64
218	Revive Anti Bacterial Instant Starch - 200 gm(MRP-65)	revive-anti-bacterial-instant-starch-200-gmmrp-65	Revive Anti Bacterial Instant Starch - 200 gm(MRP-65)	Revive Anti Bacterial Instant Starch - 200 gm(MRP-65)	DETHLDREV00000004	GF00199	8.90E+12	2	60	2019-01-08 14:12:09.949878+00	2019-01-08 14:12:09.96634+00	t	64
219	RIN Advance Powder Sapphire 150gm(MRP-10)	rin-advance-powder-sapphire-150gmmrp-10	RIN Advance Powder Sapphire 150gm(MRP-10)	RIN Advance Powder Sapphire 150gm(MRP-10)	DETHLDRIN00000001	GF01181		12	60	2019-01-08 14:12:09.98483+00	2019-01-08 14:12:10.025891+00	t	23
220	RIN BAR 75gm(MRP-5)	rin-bar-75gmmrp-5	RIN BAR 75gm(MRP-5)	RIN BAR 75gm(MRP-5)	DETHLDRIN00000002	GF01175	8.90E+12	12	144	2019-01-08 14:12:10.080417+00	2019-01-08 14:12:10.096707+00	t	23
221	RIN BAR 4X250G(MRP-64)	rin-bar-4x250gmrp-64	RIN BAR 4X250G(MRP-64)	RIN BAR 4X250G(MRP-64)	DETHLDRIN00000003	GF01195		3	12	2019-01-08 14:12:10.112074+00	2019-01-08 14:12:10.129186+00	t	23
222	Robin Liquid Blue 150 ml(MRP-50)	robin-liquid-blue-150-mlmrp-50	Robin Liquid Blue 150 ml(MRP-50)	Robin Liquid Blue 150 ml(MRP-50)	DETHLDROB00000001	GF01008	8.90E+12	3	48	2019-01-08 14:12:10.144703+00	2019-01-08 14:12:10.163507+00	t	80
223	Set Wet Cool Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	set-wet-cool-hold-hair-gel-10-ml-sachetmrp-10ea	Set Wet Cool Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	Set Wet Cool Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	HRCPCRSWT00000001	GF01673	8.90E+12	12	480	2019-01-08 14:12:10.181564+00	2019-01-08 14:12:10.199667+00	t	58
224	Set Wet Ultimate Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	set-wet-ultimate-hold-hair-gel-10-ml-sachetmrp-10ea	Set Wet Ultimate Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	Set Wet Ultimate Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	HRCPCRSWT00000002	GF01674	8.90E+12	12	480	2019-01-08 14:12:10.215722+00	2019-01-08 14:12:10.233067+00	t	58
225	Set Wet Wet Look Hair Gel, 10 ml Sachet(MRP-10)(EA)	set-wet-wet-look-hair-gel-10-ml-sachetmrp-10ea	Set Wet Wet Look Hair Gel, 10 ml Sachet(MRP-10)(EA)	Set Wet Wet Look Hair Gel, 10 ml Sachet(MRP-10)(EA)	HRCPCRSWT00000003	GF01675	8.90E+12	12	480	2019-01-08 14:12:10.248971+00	2019-01-08 14:12:10.265931+00	t	58
226	Set Wet Vertical Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	set-wet-vertical-hold-hair-gel-10-ml-sachetmrp-10ea	Set Wet Vertical Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	Set Wet Vertical Hold Hair Gel, 10 ml Sachet(MRP-10)(EA)	HRCPCRSWT00000004	GF01676		12	480	2019-01-08 14:12:10.281697+00	2019-01-08 14:12:10.298389+00	t	58
227	Set Wet Cool Hold Hair Gel, 100 ml Tube(MRP-100)	set-wet-cool-hold-hair-gel-100-ml-tubemrp-100	Set Wet Cool Hold Hair Gel, 100 ml Tube(MRP-100)	Set Wet Cool Hold Hair Gel, 100 ml Tube(MRP-100)	HRCPCRSWT00000005	GF00262	8.90E+12	3	72	2019-01-08 14:12:10.313943+00	2019-01-08 14:12:10.333679+00	t	58
228	Set Wet Cool Hold Hair Gel, 50 ml Tube(MRP-50)	set-wet-cool-hold-hair-gel-50-ml-tubemrp-50	Set Wet Cool Hold Hair Gel, 50 ml Tube(MRP-50)	Set Wet Cool Hold Hair Gel, 50 ml Tube(MRP-50)	HRCPCRSWT00000006	GF00263	8.90E+12	6	144	2019-01-08 14:12:10.34993+00	2019-01-08 14:12:10.368806+00	t	58
229	Set Wet Vertical Hold Hair Gel, 100 ml Tube(MRP-100)	set-wet-vertical-hold-hair-gel-100-ml-tubemrp-100	Set Wet Vertical Hold Hair Gel, 100 ml Tube(MRP-100)	Set Wet Vertical Hold Hair Gel, 100 ml Tube(MRP-100)	HRCPCRSWT00000007	GF00265	8.90E+12	3	72	2019-01-08 14:12:10.390311+00	2019-01-08 14:12:10.409686+00	t	58
230	Set Wet Vertical Hold Hair Gel, 50 ml Tube(MRP-50)	set-wet-vertical-hold-hair-gel-50-ml-tubemrp-50	Set Wet Vertical Hold Hair Gel, 50 ml Tube(MRP-50)	Set Wet Vertical Hold Hair Gel, 50 ml Tube(MRP-50)	HRCPCRSWT00000008	GF00266	8.90E+12	6	144	2019-01-08 14:12:10.425239+00	2019-01-08 14:12:10.445505+00	t	58
231	Set Wet Wet Look Hair Gel, 50 ml Tube(MRP-50)	set-wet-wet-look-hair-gel-50-ml-tubemrp-50	Set Wet Wet Look Hair Gel, 50 ml Tube(MRP-50)	Set Wet Wet Look Hair Gel, 50 ml Tube(MRP-50)	HRCPCRSWT00000009	GF00268	8.90E+12	6	144	2019-01-08 14:12:10.461763+00	2019-01-08 14:12:10.47959+00	t	58
232	Sunsilk Soft & Smooth Shampoo 5.5ml (MRP-1)	sunsilk-soft-smooth-shampoo-55ml-mrp-1	Sunsilk Soft & Smooth Shampoo 5.5ml (MRP-1)	Sunsilk Soft & Smooth Shampoo 5.5ml (MRP-1)	HRCPCRSUN00000001	GF01163		16	960	2019-01-08 14:12:10.495705+00	2019-01-08 14:12:10.513701+00	t	63
233	Sunsilk Thick & Long Shampoo 5.5ml(MRP-1)	sunsilk-thick-long-shampoo-55mlmrp-1	Sunsilk Thick & Long Shampoo 5.5ml(MRP-1)	Sunsilk Thick & Long Shampoo 5.5ml(MRP-1)	HRCPCRSUN00000002	GF01164	8.90E+12	16	960	2019-01-08 14:12:10.53671+00	2019-01-08 14:12:10.554029+00	t	63
234	Surf Excel Easy Wash Powder 95gm(MRP-10)	surf-excel-easy-wash-powder-95gmmrp-10	Surf Excel Easy Wash Powder 95gm(MRP-10)	Surf Excel Easy Wash Powder 95gm(MRP-10)	DETHLDSRF00000001	GF01183		12	60	2019-01-08 14:12:10.570905+00	2019-01-08 14:12:10.588446+00	t	62
235	SURF EXCEL EASY WASH 1KG	surf-excel-easy-wash-1kg	SURF EXCEL EASY WASH 1KG	SURF EXCEL EASY WASH 1KG	DETHLDSRF00000002	GF01599		3	12	2019-01-08 14:12:10.605683+00	2019-01-08 14:12:10.622749+00	t	62
236	Surf Excel Quick Wash Sachet 12gm(MRP-2)	surf-excel-quick-wash-sachet-12gmmrp-2	Surf Excel Quick Wash Sachet 12gm(MRP-2)	Surf Excel Quick Wash Sachet 12gm(MRP-2)	DETHLDSRF00000003	GF01167	8.90E+12	24	720	2019-01-08 14:12:10.637957+00	2019-01-08 14:12:10.657862+00	t	62
237	SURF EXCEL BAR 100G(MRP-10)	surf-excel-bar-100gmrp-10	SURF EXCEL BAR 100G(MRP-10)	SURF EXCEL BAR 100G(MRP-10)	DETHLDSRF00000004	GF01184	8.90E+12	12	120	2019-01-08 14:12:10.673278+00	2019-01-08 14:12:10.691713+00	t	62
238	SURF EXCEL EASY WASH CLD 500G(MRP-50)	surf-excel-easy-wash-cld-500gmrp-50	SURF EXCEL EASY WASH CLD 500G(MRP-50)	SURF EXCEL EASY WASH CLD 500G(MRP-50)	DETHLDSRF00000005	GF01598_1		4	20	2019-01-08 14:12:10.707716+00	2019-01-08 14:12:10.7248+00	t	62
239	Tide Det Powder + Jasmine & Rose 2kg  (MRP-204) Pack-12	tide-det-powder-jasmine-rose-2kg-mrp-204-pack-12	Tide Det Powder + Jasmine & Rose 2kg  (MRP-204) Pack-12	Tide Det Powder + Jasmine & Rose 2kg  (MRP-204) Pack-12	DETHLDTID00000001	GF01043	4.90E+12	1	12	2019-01-08 14:12:10.74085+00	2019-01-08 14:12:10.757526+00	t	81
240	Tide Det Powder + Regular  2kg (MRP-204) Pack-12	tide-det-powder-regular-2kg-mrp-204-pack-12	Tide Det Powder + Regular  2kg (MRP-204) Pack-12	Tide Det Powder + Regular  2kg (MRP-204) Pack-12	DETHLDTID00000002	GF01046	4.90E+12	1	12	2019-01-08 14:12:10.773351+00	2019-01-08 14:12:10.790271+00	t	81
241	Tide Det Powder + Regular  1kg (MRP-90) Pack-24	tide-det-powder-regular-1kg-mrp-90-pack-24	Tide Det Powder + Regular  1kg (MRP-90) Pack-24	Tide Det Powder + Regular  1kg (MRP-90) Pack-24	DETHLDTID00000003	GF01045_1		3	24	2019-01-08 14:12:10.805626+00	2019-01-08 14:12:10.822586+00	t	81
242	Tide Det Powder + Jasmine & Rose 500gm (MRP-51) Pack-48	tide-det-powder-jasmine-rose-500gm-mrp-51-pack-48	Tide Det Powder + Jasmine & Rose 500gm (MRP-51) Pack-48	Tide Det Powder + Jasmine & Rose 500gm (MRP-51) Pack-48	DETHLDTID00000004	GF01044_1		3	48	2019-01-08 14:12:10.841414+00	2019-01-08 14:12:10.861002+00	t	81
362	Haldiram BHUJIA 230 Gms mrp44	haldiram-bhujia-230-gms-mrp44	Haldiram BHUJIA 230 Gms mrp44	Haldiram BHUJIA 230 Gms mrp44	CNNSBFHAS00000021	GF01285	8.90406E+12	8	120	2019-01-09 04:45:25.705467+00	2019-01-09 04:45:25.722372+00	t	51
243	Tressme Hair Fall Defence Shampoo 7.5ML(MRP-3)	tressme-hair-fall-defence-shampoo-75mlmrp-3	Tressme Hair Fall Defence Shampoo 7.5ML(MRP-3)	Tressme Hair Fall Defence Shampoo 7.5ML(MRP-3)	HRCPCRTRE00000001	GF01171	8.90E+12	15	720	2019-01-08 14:12:10.87681+00	2019-01-08 14:12:10.894913+00	t	24
244	Tressme Keratin Shampoo 7.5ML(MRP-3)	tressme-keratin-shampoo-75mlmrp-3	Tressme Keratin Shampoo 7.5ML(MRP-3)	Tressme Keratin Shampoo 7.5ML(MRP-3)	HRCPCRTRE00000002	GF01172	8.90E+12	15	720	2019-01-08 14:12:10.910587+00	2019-01-08 14:12:10.928418+00	t	24
245	Tressme Smooth & Shine Shampoo 7.5ML(MRP-3)	tressme-smooth-shine-shampoo-75mlmrp-3	Tressme Smooth & Shine Shampoo 7.5ML(MRP-3)	Tressme Smooth & Shine Shampoo 7.5ML(MRP-3)	HRCPCRTRE00000003	GF01173	8.90E+12	15	720	2019-01-08 14:12:10.943593+00	2019-01-08 14:12:10.962292+00	t	24
246	Vanish oxi Action Stain Remover Liquid - 180 ml(MRP-55)	vanish-oxi-action-stain-remover-liquid-180-mlmrp-55	Vanish oxi Action Stain Remover Liquid - 180 ml(MRP-55)	Vanish oxi Action Stain Remover Liquid - 180 ml(MRP-55)	DETHLDVAN00000001	GF00671	8.90E+12	2	48	2019-01-08 14:12:10.980344+00	2019-01-08 14:12:10.997864+00	t	61
247	VASELINE DEEP STORE LOTION 20ML(MRP-10)	vaseline-deep-store-lotion-20mlmrp-10	VASELINE DEEP STORE LOTION 20ML(MRP-10)	VASELINE DEEP STORE LOTION 20ML(MRP-10)	SKCPCRVAS00000001	GF01189		12	432	2019-01-08 14:12:11.01413+00	2019-01-08 14:12:11.032196+00	t	25
248	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 25 g(MRP-61)	veet-silk-fresh-hair-removal-cream-normal-skin-25-gmrp-61	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 25 g(MRP-61)	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 25 g(MRP-61)	HRMPCRVET00000001	GF00650	8.90E+12	6	144	2019-01-08 14:12:11.047875+00	2019-01-08 14:12:11.067561+00	t	33
249	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 25 g(MRP-58)	veet-silk-fresh-hair-removal-cream-normal-skin-25-gmrp-58	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 25 g(MRP-58)	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 25 g(MRP-58)	HRMPCRVET00000002	GF00650_1	8.90E+12	6	144	2019-01-08 14:12:11.08362+00	2019-01-08 14:12:11.099625+00	t	33
250	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 50 g(MRP-115)	veet-silk-fresh-hair-removal-cream-normal-skin-50-gmrp-115	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 50 g(MRP-115)	Veet Silk & Fresh Hair Removal Cream, Normal Skin - 50 g(MRP-115)	HRMPCRVET00000003	GF00653	8.90E+12	6	72	2019-01-08 14:12:11.117057+00	2019-01-08 14:12:11.134177+00	t	33
251	VEET 25 GM MIX(MRP-61)	veet-25-gm-mixmrp-61	VEET 25 GM MIX(MRP-61)	VEET 25 GM MIX(MRP-61)	HRMPCRVET00000004	GF00718_1		6	144	2019-01-08 14:12:11.149538+00	2019-01-08 14:12:11.167074+00	t	33
252	Veet Silk & Fresh Hair Removal Cream, Sensitive Skin - 25 g(MRP-63)	veet-silk-fresh-hair-removal-cream-sensitive-skin-25-gmrp-63	Veet Silk & Fresh Hair Removal Cream, Sensitive Skin - 25 g(MRP-63)	Veet Silk & Fresh Hair Removal Cream, Sensitive Skin - 25 g(MRP-63)	HRMPCRVET00000005	GF00652_1	8.90E+12	6	144	2019-01-08 14:12:11.182373+00	2019-01-08 14:12:11.199418+00	t	33
253	Veet Silk & Fresh Hair Removal Cream, Sensitive Skin - 25 g(MRP-61)	veet-silk-fresh-hair-removal-cream-sensitive-skin-25-gmrp-61	Veet Silk & Fresh Hair Removal Cream, Sensitive Skin - 25 g(MRP-61)	Veet Silk & Fresh Hair Removal Cream, Sensitive Skin - 25 g(MRP-61)	HRMPCRVET00000006	GF00652_2	8.90E+12	6	144	2019-01-08 14:12:11.214751+00	2019-01-08 14:12:11.23269+00	t	33
254	Veet Silk & Fresh Hair Removal Cream_Dry Skin 25 g(MRP-61)	veet-silk-fresh-hair-removal-cream_dry-skin-25-gmrp-61	Veet Silk & Fresh Hair Removal Cream_Dry Skin 25 g(MRP-61)	Veet Silk & Fresh Hair Removal Cream_Dry Skin 25 g(MRP-61)	HRMPCRVET00000007	GF00651_2	8.90E+12	6	144	2019-01-08 14:12:11.248601+00	2019-01-08 14:12:11.268542+00	t	33
255	Veet Silk & Fresh Hair Removal Cream_Dry Skin 25 g(MRP-63)	veet-silk-fresh-hair-removal-cream_dry-skin-25-gmrp-63	Veet Silk & Fresh Hair Removal Cream_Dry Skin 25 g(MRP-63)	Veet Silk & Fresh Hair Removal Cream_Dry Skin 25 g(MRP-63)	HRMPCRVET00000008	GF00651_1	8.90E+12	6	144	2019-01-08 14:12:11.283939+00	2019-01-08 14:12:11.306747+00	t	33
256	Vicks Veporub 5 ml MRP 18 Pack of 12	vicks-veporub-5-ml-mrp-18-pack-of-12	Vicks Veporub 5 ml MRP 18 Pack of 12	Vicks Veporub 5 ml MRP 18 Pack of 12	EVMPCRVIC00000001	GF01049	4.99E+12	12	1200	2019-01-08 14:12:11.322084+00	2019-01-08 14:12:11.339872+00	t	82
257	VIM BAR Multipack  3X200G(MRP-40)	vim-bar-multipack-3x200gmrp-40	VIM BAR Multipack  3X200G(MRP-40)	VIM BAR Multipack  3X200G(MRP-40)	DWSHLDVIM00000001	GF01193	8.90E+12	3	20	2019-01-08 14:12:11.355361+00	2019-01-08 14:12:11.372339+00	t	60
258	VIM BAR 85G(MRP-5)	vim-bar-85gmrp-5	VIM BAR 85G(MRP-5)	VIM BAR 85G(MRP-5)	DWSHLDVIM00000002	GF01197	8.90E+12	18	144	2019-01-08 14:12:11.387972+00	2019-01-08 14:12:11.404502+00	t	60
259	VIM BAR 150G(MRP-10)	vim-bar-150gmrp-10	VIM BAR 150G(MRP-10)	VIM BAR 150G(MRP-10)	DWSHLDVIM00000003	GF01198		10	90	2019-01-08 14:12:11.421699+00	2019-01-08 14:12:11.438157+00	t	60
260	VIM LIQUID YELLOW BOTTLE REL 750ML(MRP-155)	vim-liquid-yellow-bottle-rel-750mlmrp-155	VIM LIQUID YELLOW BOTTLE REL 750ML(MRP-155)	VIM LIQUID YELLOW BOTTLE REL 750ML(MRP-155)	DWSHLDVIM00000004	GF01620		1	12	2019-01-08 14:12:11.453824+00	2019-01-08 14:12:11.470551+00	t	60
261	Vivel Aloe Vera Satinsoft Soap 100 gm (Pack of 4)(MRP-87)	vivel-aloe-vera-satinsoft-soap-100-gm-pack-of-4mrp-87	Vivel Aloe Vera Satinsoft Soap 100 gm (Pack of 4)(MRP-87)	Vivel Aloe Vera Satinsoft Soap 100 gm (Pack of 4)(MRP-87)	BBSPCRVIV00000001	GF00781	8.90E+12	3	18	2019-01-08 14:12:11.486273+00	2019-01-08 14:12:11.504001+00	t	83
262	Wheel Lemon & Orange Powder 80gm(MRP-10)	wheel-lemon-orange-powder-80gmmrp-10	Wheel Lemon & Orange Powder 80gm(MRP-10)	Wheel Lemon & Orange Powder 80gm(MRP-10)	DETHLDWHE00000001	GF01174		12	120	2019-01-08 14:12:11.520432+00	2019-01-08 14:12:11.537257+00	t	26
263	Wheel Clean & Fresh 500gm(MRP-26)	wheel-clean-fresh-500gmmrp-26	Wheel Clean & Fresh 500gm(MRP-26)	Wheel Clean & Fresh 500gm(MRP-26)	DETHLDWHE00000002	GF01552_1		6	30	2019-01-08 14:12:11.552489+00	2019-01-08 14:12:11.569249+00	t	26
264	Whisper Sanitary Pad Choice Regular 7 Pcs(MRP-29)	whisper-sanitary-pad-choice-regular-7-pcsmrp-29	Whisper Sanitary Pad Choice Regular 7 Pcs(MRP-29)	Whisper Sanitary Pad Choice Regular 7 Pcs(MRP-29)	SNTPCRWSP00000001	GF01050	4.90E+12	3	120	2019-01-08 14:12:11.584395+00	2019-01-08 14:12:11.601144+00	t	59
265	Whisper Sanitary Pad Choice Wings XL 7 Pcs(MRP-31)	whisper-sanitary-pad-choice-wings-xl-7-pcsmrp-31	Whisper Sanitary Pad Choice Wings XL 7 Pcs(MRP-31)	Whisper Sanitary Pad Choice Wings XL 7 Pcs(MRP-31)	SNTPCRWSP00000002	GF01052	4.90E+12	3	90	2019-01-08 14:12:11.616543+00	2019-01-08 14:12:11.63432+00	t	59
266	Whisper Sanitary Pad Choice Ultra 6 Pcs(MRP-39)	whisper-sanitary-pad-choice-ultra-6-pcsmrp-39	Whisper Sanitary Pad Choice Ultra 6 Pcs(MRP-39)	Whisper Sanitary Pad Choice Ultra 6 Pcs(MRP-39)	SNTPCRWSP00000003	GF01051	4.90E+12	6	96	2019-01-08 14:12:11.650001+00	2019-01-08 14:12:11.666734+00	t	59
267	Vaseline PJ 7gm(MRP-5)	vaseline-pj-7gmmrp-5	Vaseline PJ 7gm(MRP-5)	Vaseline PJ 7gm(MRP-5)	SKCPCRVAS00000002	GF01178	NA	48	768	2019-01-08 14:12:11.682324+00	2019-01-08 14:12:11.698711+00	t	25
268	Wheel Lemon & Orange Powder 500gm(MRP-26)	wheel-lemon-orange-powder-500gmmrp-26	Wheel Lemon & Orange Powder 500gm(MRP-26)	Wheel Lemon & Orange Powder 500gm(MRP-26)	DETHLDWHE00000003	GF01191		6	30	2019-01-08 14:12:11.714183+00	2019-01-08 14:12:11.730646+00	t	26
269	Wheel Lemon & Orange Powder 1KG(MRP-53)	wheel-lemon-orange-powder-1kgmrp-53	Wheel Lemon & Orange Powder 1KG(MRP-53)	Wheel Lemon & Orange Powder 1KG(MRP-53)	DETHLDWHE00000004	GF01194		5	25	2019-01-08 14:12:11.74604+00	2019-01-08 14:12:11.762471+00	t	26
275	LACTOGEN Stage 1 Infant Formula Box 400g	lactogen-stage-1-infant-formula-box-400g	LACTOGEN Stage 1 Infant Formula Box 400g	LACTOGEN Stage 1 Infant Formula Box 400g	BBFINFLAC00000002	GF01532	8.90106E+12	1	24	2019-01-09 04:45:22.76389+00	2019-01-09 04:45:22.780295+00	t	38
276	MAGGI 2-MIN Masala Noodles 140g	maggi-2-min-masala-noodles-140g	MAGGI 2-MIN Masala Noodles 140g	MAGGI 2-MIN Masala Noodles 140g	NPVSBFMAG00000002	GF01533	8.90106E+12	6	48	2019-01-09 04:45:22.796036+00	2019-01-09 04:45:22.811767+00	t	35
277	MAGGI 2-MIN Masala Noodles 280g	maggi-2-min-masala-noodles-280g	MAGGI 2-MIN Masala Noodles 280g	MAGGI 2-MIN Masala Noodles 280g	NPVSBFMAG00000003	GF01534	8.90106E+12	6	24	2019-01-09 04:45:22.829933+00	2019-01-09 04:45:22.849673+00	t	35
278	MAGGI 2-MIN Masala Noodles 280g	maggi-2-min-masala-noodles-280g	MAGGI 2-MIN Masala Noodles 280g	MAGGI 2-MIN Masala Noodles 280g	NPVSBFMAG00000004	GF01534_1		6	24	2019-01-09 04:45:22.864156+00	2019-01-09 04:45:22.882397+00	t	35
279	CERELAC STAGE 2 Wheat Apple Cherry Box 300g	cerelac-stage-2-wheat-apple-cherry-box-300g	CERELAC STAGE 2 Wheat Apple Cherry Box 300g	CERELAC STAGE 2 Wheat Apple Cherry Box 300g	BBFINFCER00000002	GF01572	8.90106E+12	1	24	2019-01-09 04:45:22.897215+00	2019-01-09 04:45:22.91313+00	t	37
280	CERELAC STAGE 4 5-Fruit Box 300g	cerelac-stage-4-5-fruit-box-300g	CERELAC STAGE 4 5-Fruit Box 300g	CERELAC STAGE 4 5-Fruit Box 300g	BBFINFCER00000003	GF01582	8.90106E+12	1	24	2019-01-09 04:45:22.932007+00	2019-01-09 04:45:22.947511+00	t	37
281	CERELAC STAGE 5 5 Grains 5 Fruits Box 300g	cerelac-stage-5-5-grains-5-fruits-box-300g	CERELAC STAGE 5 5 Grains 5 Fruits Box 300g	CERELAC STAGE 5 5 Grains 5 Fruits Box 300g	BBFINFCER00000004	GF01574	8.90106E+12	1	24	2019-01-09 04:45:22.961919+00	2019-01-09 04:45:22.982188+00	t	37
282	LACTOGEN Stage 2 Follow-up Infant Formula  Box 400g	lactogen-stage-2-follow-up-infant-formula-box-400g	LACTOGEN Stage 2 Follow-up Infant Formula  Box 400g	LACTOGEN Stage 2 Follow-up Infant Formula  Box 400g	BBFINFLAC00000003	GF01575	8.90106E+12	1	24	2019-01-09 04:45:22.996764+00	2019-01-09 04:45:23.012405+00	t	38
283	LACTOGEN Stage 3 Follow-up Infant Formula  Box 400g	lactogen-stage-3-follow-up-infant-formula-box-400g	LACTOGEN Stage 3 Follow-up Infant Formula  Box 400g	LACTOGEN Stage 3 Follow-up Infant Formula  Box 400g	BBFINFLAC00000004	GF01576	8.90106E+12	1	24	2019-01-09 04:45:23.032211+00	2019-01-09 04:45:23.047696+00	t	38
284	LACTOGEN Stage 4 Follow-up Infant Formula  Box 400g	lactogen-stage-4-follow-up-infant-formula-box-400g	LACTOGEN Stage 4 Follow-up Infant Formula  Box 400g	LACTOGEN Stage 4 Follow-up Infant Formula  Box 400g	BBFINFLAC00000005	GF01577	8.90106E+12	1	24	2019-01-09 04:45:23.062215+00	2019-01-09 04:45:23.082563+00	t	38
285	MAGGI Pichkoo Masala Imli Doy	maggi-pichkoo-masala-imli-doy	MAGGI Pichkoo Masala Imli Doy	MAGGI Pichkoo Masala Imli Doy	KSCSBFMAG00000002	GF01557	8.90106E+12	12	72	2019-01-09 04:45:23.097292+00	2019-01-09 04:45:23.112612+00	t	35
286	ITC Sunfeast Bounce Delight Cream Biscuits, Elaichi, 41g mrp5	itc-sunfeast-bounce-delight-cream-biscuits-elaichi-41g-mrp5	ITC Sunfeast Bounce Delight Cream Biscuits, Elaichi, 41g mrp5	ITC Sunfeast Bounce Delight Cream Biscuits, Elaichi, 41g mrp5	BACSBFSNF00000001	GF01344	8.90173E+12	12	144	2019-01-09 04:45:23.13349+00	2019-01-09 04:45:23.149198+00	t	40
287	ITC Sunfeast Moms Magic Biscuit, Cashew and Almond, 60.8g mrp10	itc-sunfeast-moms-magic-biscuit-cashew-and-almond-608g-mrp10	ITC Sunfeast Moms Magic Biscuit, Cashew and Almond, 60.8g mrp10	ITC Sunfeast Moms Magic Biscuit, Cashew and Almond, 60.8g mrp10	BACSBFSNF00000002	GF01345	8.90173E+12	12	72	2019-01-09 04:45:23.163739+00	2019-01-09 04:45:23.185033+00	t	40
288	ITC Bingo Potato Chips, Original Style Red Chilli sprinkled, 30g mrp10	itc-bingo-potato-chips-original-style-red-chilli-sprinkled-30g-mrp10	ITC Bingo Potato Chips, Original Style Red Chilli sprinkled, 30g mrp10	ITC Bingo Potato Chips, Original Style Red Chilli sprinkled, 30g mrp10	CNNSBFBNG00000001	GF01346	8.90173E+12	9	108	2019-01-09 04:45:23.199908+00	2019-01-09 04:45:23.216106+00	t	41
289	ITC Bingo Mad Angles Tomato Madness Namkeen, 45g mrp10	itc-bingo-mad-angles-tomato-madness-namkeen-45g-mrp10	ITC Bingo Mad Angles Tomato Madness Namkeen, 45g mrp10	ITC Bingo Mad Angles Tomato Madness Namkeen, 45g mrp10	CNNSBFBNG00000002	GF01347	8.90173E+12	9	108	2019-01-09 04:45:23.233126+00	2019-01-09 04:45:23.252074+00	t	41
290	ITC Bingo Mad Angles Achaari Masti, 45g Pouch mrp10	itc-bingo-mad-angles-achaari-masti-45g-pouch-mrp10	ITC Bingo Mad Angles Achaari Masti, 45g Pouch mrp10	ITC Bingo Mad Angles Achaari Masti, 45g Pouch mrp10	CNNSBFBNG00000003	GF01348	8.90173E+12	9	108	2019-01-09 04:45:23.267087+00	2019-01-09 04:45:23.284476+00	t	41
291	ITC Sunfeast Dark Fantasy Chocolate, 100g mrp30	itc-sunfeast-dark-fantasy-chocolate-100g-mrp30	ITC Sunfeast Dark Fantasy Chocolate, 100g mrp30	ITC Sunfeast Dark Fantasy Chocolate, 100g mrp30	BACSBFSNF00000003	GF01349	8.90173E+12	4	64	2019-01-09 04:45:23.300476+00	2019-01-09 04:45:23.316623+00	t	40
292	ITC Yippee Magic Masala Noodles, 60 g mrp10	itc-yippee-magic-masala-noodles-60-g-mrp10	ITC Yippee Magic Masala Noodles, 60 g mrp10	ITC Yippee Magic Masala Noodles, 60 g mrp10	NPVSBFYIP00000001	GF01350	8.90173E+12	12	96	2019-01-09 04:45:23.331192+00	2019-01-09 04:45:23.346598+00	t	42
293	ITC Yippee Classic Masala Noodles, 70 g mrp12	itc-yippee-classic-masala-noodles-70-g-mrp12	ITC Yippee Classic Masala Noodles, 70 g mrp12	ITC Yippee Classic Masala Noodles, 70 g mrp12	BACSBFYIP00000001	GF01351	8.90173E+12	12	96	2019-01-09 04:45:23.364456+00	2019-01-09 04:45:23.385907+00	t	42
294	ITC Sunfeast Dark Fantasy Choco Meltz, 50 g mrp25	itc-sunfeast-dark-fantasy-choco-meltz-50-g-mrp25	ITC Sunfeast Dark Fantasy Choco Meltz, 50 g mrp25	ITC Sunfeast Dark Fantasy Choco Meltz, 50 g mrp25	BACSBFSNF00000004	GF01352	8.90173E+12	3	60	2019-01-09 04:45:23.400833+00	2019-01-09 04:45:23.416857+00	t	40
295	ITC Sunfeast Dark Fantasy Choco Fills, 25g mrp10	itc-sunfeast-dark-fantasy-choco-fills-25g-mrp10	ITC Sunfeast Dark Fantasy Choco Fills, 25g mrp10	ITC Sunfeast Dark Fantasy Choco Fills, 25g mrp10	BACSBFSNF00000005	GF01353	8.90173E+12	6	120	2019-01-09 04:45:23.43163+00	2019-01-09 04:45:23.447497+00	t	40
296	Sunfeast Dark Fantasy Choco Fills, 75g mrp10	sunfeast-dark-fantasy-choco-fills-75g-mrp10	Sunfeast Dark Fantasy Choco Fills, 75g mrp10	Sunfeast Dark Fantasy Choco Fills, 75g mrp10	BACSBFSNF00000006	GF01621_1		4	64	2019-01-09 04:45:23.463633+00	2019-01-09 04:45:23.480501+00	t	40
297	ITC Yippee Power Up Noodles, Masala, 70g mrp15	itc-yippee-power-up-noodles-masala-70g-mrp15	ITC Yippee Power Up Noodles, Masala, 70g mrp15	ITC Yippee Power Up Noodles, Masala, 70g mrp15	NPVSBFYIP00000002	GF01354	8.90173E+12	12	96	2019-01-09 04:45:23.496775+00	2019-01-09 04:45:23.515695+00	t	42
298	ITC Sunfeast Dreamcream Strawberry Vanilla, 120 g mrp20	itc-sunfeast-dreamcream-strawberry-vanilla-120-g-mrp20	ITC Sunfeast Dreamcream Strawberry Vanilla, 120 g mrp20	ITC Sunfeast Dreamcream Strawberry Vanilla, 120 g mrp20	BACSBFSNF00000007	GF01355	8.90173E+12	6	48	2019-01-09 04:45:23.530601+00	2019-01-09 04:45:23.547464+00	t	40
299	ITC Sunfeast Dream Cream Bourbon Bliss, 60g mrp10	itc-sunfeast-dream-cream-bourbon-bliss-60g-mrp10	ITC Sunfeast Dream Cream Bourbon Bliss, 60g mrp10	ITC Sunfeast Dream Cream Bourbon Bliss, 60g mrp10	BACSBFSNF00000008	GF01356	8.90173E+12	6	48	2019-01-09 04:45:23.562121+00	2019-01-09 04:45:23.579205+00	t	40
300	ITC Sunfeast Dream Cream Bourbon Bliss, 120g mrp20	itc-sunfeast-dream-cream-bourbon-bliss-120g-mrp20	ITC Sunfeast Dream Cream Bourbon Bliss, 120g mrp20	ITC Sunfeast Dream Cream Bourbon Bliss, 120g mrp20	BACSBFSNF00000009	GF01357	8.90173E+12	6	60	2019-01-09 04:45:23.595382+00	2019-01-09 04:45:23.611602+00	t	40
301	ITC Sunfeast Marie Light Original, 70g (with Free 15g) mrp10	itc-sunfeast-marie-light-original-70g-with-free-15g-mrp10	ITC Sunfeast Marie Light Original, 70g (with Free 15g) mrp10	ITC Sunfeast Marie Light Original, 70g (with Free 15g) mrp10	BACSBFSNF00000010	GF01358	8.90173E+12	6	30	2019-01-09 04:45:23.626465+00	2019-01-09 04:45:23.642316+00	t	40
302	ITC Sunfeast Dreamcream Strawberry Vanilla, 120 g mrp20	itc-sunfeast-dreamcream-strawberry-vanilla-120-g-mrp20	ITC Sunfeast Dreamcream Strawberry Vanilla, 120 g mrp20	ITC Sunfeast Dreamcream Strawberry Vanilla, 120 g mrp20	BACSBFSNF00000011	GF01359		6	48	2019-01-09 04:45:23.657199+00	2019-01-09 04:45:23.673551+00	t	40
303	ITC Sunfeast Moms Magic Rich Butter, 76 g mrp10	itc-sunfeast-moms-magic-rich-butter-76-g-mrp10	ITC Sunfeast Moms Magic Rich Butter, 76 g mrp10	ITC Sunfeast Moms Magic Rich Butter, 76 g mrp10	BACSBFSNF00000012	GF01360	8.90173E+12	72	12	2019-01-09 04:45:23.689002+00	2019-01-09 04:45:23.70481+00	t	40
304	ITC Sunfeast Moms Magic Rich Butter, 150 g mrp20	itc-sunfeast-moms-magic-rich-butter-150-g-mrp20	ITC Sunfeast Moms Magic Rich Butter, 150 g mrp20	ITC Sunfeast Moms Magic Rich Butter, 150 g mrp20	BACSBFSNF00000013	GF01361	8.90173E+12	6	48	2019-01-09 04:45:23.719398+00	2019-01-09 04:45:23.735254+00	t	40
305	ITC Sunfeast Bounce Choco Twist, 82 g mrp10	itc-sunfeast-bounce-choco-twist-82-g-mrp10	ITC Sunfeast Bounce Choco Twist, 82 g mrp10	ITC Sunfeast Bounce Choco Twist, 82 g mrp10	BACSBFSNF00000014	GF01362	8.90173E+12	12	72	2019-01-09 04:45:23.749989+00	2019-01-09 04:45:23.766195+00	t	40
306	ITC Sunfeast Bounce Cream Choco Twist, 82 g mrp10	itc-sunfeast-bounce-cream-choco-twist-82-g-mrp10	ITC Sunfeast Bounce Cream Choco Twist, 82 g mrp10	ITC Sunfeast Bounce Cream Choco Twist, 82 g mrp10	BACSBFSNF00000015	GF01363	8.90173E+12	12	72	2019-01-09 04:45:23.780747+00	2019-01-09 04:45:23.796682+00	t	40
307	ITC Sunfeast Dark Fantasy Vanilla, 100g mrp 25	itc-sunfeast-dark-fantasy-vanilla-100g-mrp-25	ITC Sunfeast Dark Fantasy Vanilla, 100g mrp 25	ITC Sunfeast Dark Fantasy Vanilla, 100g mrp 25	BACSBFSNF00000016	GF01364	8.90173E+12	6	60	2019-01-09 04:45:23.812767+00	2019-01-09 04:45:23.829935+00	t	40
308	ITC Sunfeast Moms Magic Cashew and Almonds, 100g mrp20	itc-sunfeast-moms-magic-cashew-and-almonds-100g-mrp20	ITC Sunfeast Moms Magic Cashew and Almonds, 100g mrp20	ITC Sunfeast Moms Magic Cashew and Almonds, 100g mrp20	BACSBFSNF00000017	GF01365	8.90173E+12	6	60	2019-01-09 04:45:23.844941+00	2019-01-09 04:45:23.861989+00	t	40
309	ITC Bingo Yumitos Salted Potato Chips ,52g mrp20	itc-bingo-yumitos-salted-potato-chips-52g-mrp20	ITC Bingo Yumitos Salted Potato Chips ,52g mrp20	ITC Bingo Yumitos Salted Potato Chips ,52g mrp20	CNNSBFBNG00000004	GF01366	8.90173E+12	6	48	2019-01-09 04:45:23.876321+00	2019-01-09 04:45:23.892761+00	t	41
310	ITC Bingo Mad Angles Masala Madness Namkeen, 90 g mrp20	itc-bingo-mad-angles-masala-madness-namkeen-90-g-mrp20	ITC Bingo Mad Angles Masala Madness Namkeen, 90 g mrp20	ITC Bingo Mad Angles Masala Madness Namkeen, 90 g mrp20	CNNSBFBNG00000005	GF01367	8.90173E+12	8	56	2019-01-09 04:45:23.908104+00	2019-01-09 04:45:23.925136+00	t	41
311	ITC Bingo Potato chips Tomato, 52 g mrp20	itc-bingo-potato-chips-tomato-52-g-mrp20	ITC Bingo Potato chips Tomato, 52 g mrp20	ITC Bingo Potato chips Tomato, 52 g mrp20	CNNSBFBNG00000006	GF01368	8.90173E+12	8	48	2019-01-09 04:45:23.941189+00	2019-01-09 04:45:23.958619+00	t	41
312	ITC Bingo Mad Angles Achaari Masti Namkeen, 80g mrp20	itc-bingo-mad-angles-achaari-masti-namkeen-80g-mrp20	ITC Bingo Mad Angles Achaari Masti Namkeen, 80g mrp20	ITC Bingo Mad Angles Achaari Masti Namkeen, 80g mrp20	CNNSBFBNG00000007	GF01369	8.90173E+12	8	56	2019-01-09 04:45:23.97508+00	2019-01-09 04:45:23.99257+00	t	41
313	ITC Bingo Potato Chips Cream & Onion, 52g mrp20	itc-bingo-potato-chips-cream-onion-52g-mrp20	ITC Bingo Potato Chips Cream & Onion, 52g mrp20	ITC Bingo Potato Chips Cream & Onion, 52g mrp20	CNNSBFBNG00000008	GF01370	8.90173E+12	8	48	2019-01-09 04:45:24.010444+00	2019-01-09 04:45:24.026845+00	t	41
314	ITC Bingo Tedhe Medhe Masala Tadka Namkeen, 54g (36g + 18g Extra) mrp10	itc-bingo-tedhe-medhe-masala-tadka-namkeen-54g-36g-18g-extra-mrp10	ITC Bingo Tedhe Medhe Masala Tadka Namkeen, 54g (36g + 18g Extra) mrp10	ITC Bingo Tedhe Medhe Masala Tadka Namkeen, 54g (36g + 18g Extra) mrp10	CNNSBFBNG00000009	GF01628		8	80	2019-01-09 04:45:24.045384+00	2019-01-09 04:45:24.064363+00	t	41
315	ITC Bingo Tedhe Medhe Achaari Masti Namkeen, 54g mrp10	itc-bingo-tedhe-medhe-achaari-masti-namkeen-54g-mrp10	ITC Bingo Tedhe Medhe Achaari Masti Namkeen, 54g mrp10	ITC Bingo Tedhe Medhe Achaari Masti Namkeen, 54g mrp10	CNNSBFBNG00000010	GF01629	8.90173E+12	8	80	2019-01-09 04:45:24.079763+00	2019-01-09 04:45:24.099755+00	t	41
316	ITC Bingo Tedhe Medhe Mast Masala Tadka, 108g mrp20	itc-bingo-tedhe-medhe-mast-masala-tadka-108g-mrp20	ITC Bingo Tedhe Medhe Mast Masala Tadka, 108g mrp20	ITC Bingo Tedhe Medhe Mast Masala Tadka, 108g mrp20	CNNSBFBNG00000011	GF01630	8.90173E+12	8	40	2019-01-09 04:45:24.115078+00	2019-01-09 04:45:24.131022+00	t	41
317	Kelloggs Corn Flakes 26g (MRP 10)	kelloggs-corn-flakes-26g-mrp-10	Kelloggs Corn Flakes 26g (MRP 10)	Kelloggs Corn Flakes 26g (MRP 10)	BFCSBFCNF00000001	GF01591		12	180	2019-01-09 04:45:24.145676+00	2019-01-09 04:45:24.16378+00	t	44
318	Kelloggs Corn Flakes 70g (MRP 20)	kelloggs-corn-flakes-70g-mrp-20	Kelloggs Corn Flakes 70g (MRP 20)	Kelloggs Corn Flakes 70g (MRP 20)	BFCSBFCNF00000002	GF01423		12	96	2019-01-09 04:45:24.178185+00	2019-01-09 04:45:24.194303+00	t	44
319	Kelloggs Corn Flakes 100g (MRP 38)	kelloggs-corn-flakes-100g-mrp-38	Kelloggs Corn Flakes 100g (MRP 38)	Kelloggs Corn Flakes 100g (MRP 38)	BFCSBFCNF00000003	GF01424	8.9015E+12	6	36	2019-01-09 04:45:24.212741+00	2019-01-09 04:45:24.229317+00	t	44
320	Kelloggs Corn Flakes 475g (MRP 175)	kelloggs-corn-flakes-475g-mrp-175	Kelloggs Corn Flakes 475g (MRP 175)	Kelloggs Corn Flakes 475g (MRP 175)	BFCSBFCNF00000004	GF01425		4	12	2019-01-09 04:45:24.245244+00	2019-01-09 04:45:24.261524+00	t	44
321	Kelloggs Chocos Fills 35g (MRP 20)	kelloggs-chocos-fills-35g-mrp-20	Kelloggs Chocos Fills 35g (MRP 20)	Kelloggs Chocos Fills 35g (MRP 20)	BFCSBFCHO00000001	GF01426		12	180	2019-01-09 04:45:24.2822+00	2019-01-09 04:45:24.297954+00	t	45
322	Kelloggs Chocos 26g (MRP 10)	kelloggs-chocos-26g-mrp-10	Kelloggs Chocos 26g (MRP 10)	Kelloggs Chocos 26g (MRP 10)	BFCSBFCHO00000002	GF01427	8.9015E+12	16	192	2019-01-09 04:45:24.313+00	2019-01-09 04:45:24.329249+00	t	45
323	Kelloggs Chocos 60g (MRP 20)	kelloggs-chocos-60g-mrp-20	Kelloggs Chocos 60g (MRP 20)	Kelloggs Chocos 60g (MRP 20)	BFCSBFCHO00000003	GF01428		12	96	2019-01-09 04:45:24.343808+00	2019-01-09 04:45:24.360761+00	t	45
324	Kelloggs Chocos 250g (MRP 115)	kelloggs-chocos-250g-mrp-115	Kelloggs Chocos 250g (MRP 115)	Kelloggs Chocos 250g (MRP 115)	BFCSBFCHO00000004	GF01429		4	16	2019-01-09 04:45:24.382018+00	2019-01-09 04:45:24.397815+00	t	45
325	Kelloggs Chocos 375g (MRP 160)	kelloggs-chocos-375g-mrp-160	Kelloggs Chocos 375g (MRP 160)	Kelloggs Chocos 375g (MRP 160)	BFCSBFCHO00000005	GF01430		4	16	2019-01-09 04:45:24.412726+00	2019-01-09 04:45:24.429008+00	t	45
326	Kelloggs Chocos 700g (MRP 280)	kelloggs-chocos-700g-mrp-280	Kelloggs Chocos 700g (MRP 280)	Kelloggs Chocos 700g (MRP 280)	BFCSBFCHO00000006	GF01431		2	12	2019-01-09 04:45:24.444739+00	2019-01-09 04:45:24.46152+00	t	45
327	Kelloggs Chocos 1200g (MRP 445)	kelloggs-chocos-1200g-mrp-445	Kelloggs Chocos 1200g (MRP 445)	Kelloggs Chocos 1200g (MRP 445)	BFCSBFCHO00000007	GF01432		1	6	2019-01-09 04:45:24.477767+00	2019-01-09 04:45:24.494818+00	t	45
328	Kelloggs Chocos Duet 26g (MRP 10)	kelloggs-chocos-duet-26g-mrp-10	Kelloggs Chocos Duet 26g (MRP 10)	Kelloggs Chocos Duet 26g (MRP 10)	BFCSBFCHO00000008	GF01433		16	192	2019-01-09 04:45:24.509998+00	2019-01-09 04:45:24.52605+00	t	45
363	Haldiram punjabi tadka mrp5	haldiram-punjabi-tadka-mrp5	Haldiram punjabi tadka mrp5	Haldiram punjabi tadka mrp5	CNNSBFHAS00000022	GF01286	8.90406E+12	12	504	2019-01-09 04:45:25.737611+00	2019-01-09 04:45:25.753801+00	t	51
329	Kelloggs Chocos Duet 375g (MRP 170)	kelloggs-chocos-duet-375g-mrp-170	Kelloggs Chocos Duet 375g (MRP 170)	Kelloggs Chocos Duet 375g (MRP 170)	BFCSBFCHO00000009	GF01434		1	16	2019-01-09 04:45:24.540838+00	2019-01-09 04:45:24.558022+00	t	45
342	Haldiram aloo bhuji mrp5	haldiram-aloo-bhuji-mrp5	Haldiram aloo bhuji mrp5	Haldiram aloo bhuji mrp5	CNNSBFHAS00000001	GF01265	8.90406E+12	12	504	2019-01-09 04:45:24.986801+00	2019-01-09 07:45:38.167492+00	t	51
330	Lays  Maxx - Sizzling Barbeque -58g Pack	lays-maxx-sizzling-barbeque-58g-pack	Lays  Maxx - Sizzling Barbeque -58g Pack	Lays  Maxx - Sizzling Barbeque -58g Pack	CNNSBFLAY00000001	GF00533	8.90149E+12	8	56	2019-01-09 04:45:24.572464+00	2019-01-09 04:45:24.588266+00	t	47
343	Haldiram Bikaneri bhujia mrp5	haldiram-bikaneri-bhujia-mrp5	Haldiram Bikaneri bhujia mrp5	Haldiram Bikaneri bhujia mrp5	CNNSBFHAS00000002	GF01266	8.90406E+12	12	504	2019-01-09 04:45:25.053426+00	2019-01-09 07:47:52.527595+00	t	51
331	Lays  Maxx - Macho Chilli - 58gm Pack	lays-maxx-macho-chilli-58gm-pack	Lays  Maxx - Macho Chilli - 58gm Pack	Lays  Maxx - Macho Chilli - 58gm Pack	CNNSBFLAY00000002	GF00534	8.90149E+12	8	56	2019-01-09 04:45:24.603795+00	2019-01-09 04:45:24.619229+00	t	47
332	Lays  Maxx - Macho Chilli - 30gm Pack	lays-maxx-macho-chilli-30gm-pack	Lays  Maxx - Macho Chilli - 30gm Pack	Lays  Maxx - Macho Chilli - 30gm Pack	CNNSBFLAY00000003	GF00535	8.90149E+12	8	48	2019-01-09 04:45:24.634343+00	2019-01-09 04:45:24.650282+00	t	47
333	Lays  Maxx - Hot N Sour Punch -33g Pack	lays-maxx-hot-n-sour-punch-33g-pack	Lays  Maxx - Hot N Sour Punch -33g Pack	Lays  Maxx - Hot N Sour Punch -33g Pack	CNNSBFLAY00000004	GF00536	8.90149E+12	8	48	2019-01-09 04:45:24.665641+00	2019-01-09 04:45:24.681318+00	t	47
334	Lays  Maxx - Hot N Sour Punch -58g Pack	lays-maxx-hot-n-sour-punch-58g-pack	Lays  Maxx - Hot N Sour Punch -58g Pack	Lays  Maxx - Hot N Sour Punch -58g Pack	CNNSBFLAY00000005	GF00537	8.90149E+12	8	56	2019-01-09 04:45:24.69583+00	2019-01-09 04:45:24.713826+00	t	47
335	Doritos Nacho Cheese, 39g	doritos-nacho-cheese-39g	Doritos Nacho Cheese, 39g	Doritos Nacho Cheese, 39g	CNNSBFDOR00000001	GF00431	8.90149E+12	8	48	2019-01-09 04:45:24.72943+00	2019-01-09 04:45:24.747665+00	t	48
336	Doritos Sweet Chilli, 39gms	doritos-sweet-chilli-39gms	Doritos Sweet Chilli, 39gms	Doritos Sweet Chilli, 39gms	CNNSBFDOR00000002	GF00433	8.90149E+12	8	48	2019-01-09 04:45:24.763128+00	2019-01-09 04:45:24.779166+00	t	48
337	Lays  Potato Chips - Classic Salted - 30 gm  Pack	lays-potato-chips-classic-salted-30-gm-pack	Lays  Potato Chips - Classic Salted - 30 gm  Pack	Lays  Potato Chips - Classic Salted - 30 gm  Pack	CNNSBFLAY00000006	GF00516	8.90149E+12	9	81	2019-01-09 04:45:24.795031+00	2019-01-09 04:45:24.813841+00	t	47
338	Lays  Potato Chips - Spanish Tomato Tango - 30 gm Pack	lays-potato-chips-spanish-tomato-tango-30-gm-pack	Lays  Potato Chips - Spanish Tomato Tango - 30 gm Pack	Lays  Potato Chips - Spanish Tomato Tango - 30 gm Pack	CNNSBFLAY00000007	GF00517	8.90149E+12	9	81	2019-01-09 04:45:24.829479+00	2019-01-09 04:45:24.861856+00	t	47
339	Lays  Potato Chips - American Style Cream & Onion Flavour - 30g Pack	lays-potato-chips-american-style-cream-onion-flavour-30g-pack	Lays  Potato Chips - American Style Cream & Onion Flavour - 30g Pack	Lays  Potato Chips - American Style Cream & Onion Flavour - 30g Pack	CNNSBFLAY00000008	GF00519	8.90149E+12	9	81	2019-01-09 04:45:24.876612+00	2019-01-09 04:45:24.892142+00	t	47
340	Lays  Potato Chips - India Magic Masala - 30gm Pack	lays-potato-chips-india-magic-masala-30gm-pack	Lays  Potato Chips - India Magic Masala - 30gm Pack	Lays  Potato Chips - India Magic Masala - 30gm Pack	CNNSBFLAY00000009	GF00520	8.90149E+12	9	81	2019-01-09 04:45:24.907872+00	2019-01-09 04:45:24.928874+00	t	47
341	Quaker Oats - 400 gm	quaker-oats-400-gm	Quaker Oats - 400 gm	Quaker Oats - 400 gm	BFCSBFQKR00000001	GF00543	8.90149E+12	4	24	2019-01-09 04:45:24.948761+00	2019-01-09 04:45:24.964632+00	t	49
344	Haldiram Khatta Meetha mrp5	haldiram-khatta-meetha-mrp5	Haldiram Khatta Meetha mrp5	Haldiram Khatta Meetha mrp5	CNNSBFHAS00000003	GF01267	8.90406E+12	12	504	2019-01-09 04:45:25.090126+00	2019-01-09 04:45:25.109863+00	t	51
345	Haldiram navrattan mrp5	haldiram-navrattan-mrp5	Haldiram navrattan mrp5	Haldiram navrattan mrp5	CNNSBFHAS00000004	GF01268	8.90406E+12	12	504	2019-01-09 04:45:25.125431+00	2019-01-09 04:45:25.14191+00	t	51
346	Haldiram moongdaal mrp5	haldiram-moongdaal-mrp5	Haldiram moongdaal mrp5	Haldiram moongdaal mrp5	CNNSBFHAS00000005	GF01269	8.90406E+12	12	504	2019-01-09 04:45:25.163432+00	2019-01-09 04:45:25.179727+00	t	51
347	Haldiram salted peanut mrp5	haldiram-salted-peanut-mrp5	Haldiram salted peanut mrp5	Haldiram salted peanut mrp5	CNNSBFHAS00000006	GF01270	8.90406E+12	12	504	2019-01-09 04:45:25.194839+00	2019-01-09 04:45:25.21272+00	t	51
348	Haldiram diet mix mrp5	haldiram-diet-mix-mrp5	Haldiram diet mix mrp5	Haldiram diet mix mrp5	CNNSBFHAS00000007	GF01271	8.90406E+12	12	504	2019-01-09 04:45:25.227827+00	2019-01-09 04:45:25.244056+00	t	51
349	Haldiram Diet Chiwda mrp5	haldiram-diet-chiwda-mrp5	Haldiram Diet Chiwda mrp5	Haldiram Diet Chiwda mrp5	CNNSBFHAS00000008	GF01272	8.90406E+12	12	504	2019-01-09 04:45:25.259347+00	2019-01-09 04:45:25.277794+00	t	51
350	Haldiram aloo bhuji mrp10	haldiram-aloo-bhuji-mrp10	Haldiram aloo bhuji mrp10	Haldiram aloo bhuji mrp10	CNNSBFHAS00000009	GF01273	8.90406E+12	10	300	2019-01-09 04:45:25.293618+00	2019-01-09 04:45:25.310981+00	t	51
351	Haldiram Bikaneri bhujia mrp10	haldiram-bikaneri-bhujia-mrp10	Haldiram Bikaneri bhujia mrp10	Haldiram Bikaneri bhujia mrp10	CNNSBFHAS00000010	GF01274	8.90406E+12	10	300	2019-01-09 04:45:25.325472+00	2019-01-09 04:45:25.343961+00	t	51
352	Haldiram Khatta Meetha mrp10	haldiram-khatta-meetha-mrp10	Haldiram Khatta Meetha mrp10	Haldiram Khatta Meetha mrp10	CNNSBFHAS00000011	GF01275	8.90406E+12	10	300	2019-01-09 04:45:25.358728+00	2019-01-09 04:45:25.373896+00	t	51
353	Haldiram navrattan mrp10	haldiram-navrattan-mrp10	Haldiram navrattan mrp10	Haldiram navrattan mrp10	CNNSBFHAS00000012	GF01276	8.90406E+12	10	300	2019-01-09 04:45:25.393672+00	2019-01-09 04:45:25.41256+00	t	51
354	Haldiram moongdaal mrp10	haldiram-moongdaal-mrp10	Haldiram moongdaal mrp10	Haldiram moongdaal mrp10	CNNSBFHAS00000013	GF01277	8.90406E+12	10	300	2019-01-09 04:45:25.435726+00	2019-01-09 04:45:25.452486+00	t	51
355	Haldiram salted peanut mrp10	haldiram-salted-peanut-mrp10	Haldiram salted peanut mrp10	Haldiram salted peanut mrp10	CNNSBFHAS00000014	GF01278	8.90406E+12	10	300	2019-01-09 04:45:25.470018+00	2019-01-09 04:45:25.487477+00	t	51
356	Haldiram diet mix mrp10	haldiram-diet-mix-mrp10	Haldiram diet mix mrp10	Haldiram diet mix mrp10	CNNSBFHAS00000015	GF01279	8.90406E+12	10	300	2019-01-09 04:45:25.503046+00	2019-01-09 04:45:25.523523+00	t	51
357	Haldiram Diet Chiwda mrp10	haldiram-diet-chiwda-mrp10	Haldiram Diet Chiwda mrp10	Haldiram Diet Chiwda mrp10	CNNSBFHAS00000016	GF01280	8.90406E+12	10	300	2019-01-09 04:45:25.540583+00	2019-01-09 04:45:25.556405+00	t	51
358	Haldiram Tasty Gupshup mrp10	haldiram-tasty-gupshup-mrp10	Haldiram Tasty Gupshup mrp10	Haldiram Tasty Gupshup mrp10	CNNSBFHAS00000017	GF01281	8.90406E+12	10	300	2019-01-09 04:45:25.572857+00	2019-01-09 04:45:25.58939+00	t	51
359	Haldiram punjabi tadka mrp10	haldiram-punjabi-tadka-mrp10	Haldiram punjabi tadka mrp10	Haldiram punjabi tadka mrp10	CNNSBFHAS00000018	GF01282	8.90406E+12	10	300	2019-01-09 04:45:25.604496+00	2019-01-09 04:45:25.621027+00	t	51
360	Haldiram Tasty Gupshup mrp5	haldiram-tasty-gupshup-mrp5	Haldiram Tasty Gupshup mrp5	Haldiram Tasty Gupshup mrp5	CNNSBFHAS00000019	GF01283	8.90406E+12	12	504	2019-01-09 04:45:25.639585+00	2019-01-09 04:45:25.657466+00	t	51
361	Haldiram ALOO BHUJIA 230 Gms mrp44	haldiram-aloo-bhujia-230-gms-mrp44	Haldiram ALOO BHUJIA 230 Gms mrp44	Haldiram ALOO BHUJIA 230 Gms mrp44	CNNSBFHAS00000020	GF01284	8.90406E+12	8	120	2019-01-09 04:45:25.673589+00	2019-01-09 04:45:25.689501+00	t	51
382	Tide Laundary Powder Lemon & Mint 110gm(MRP-10) Pack-12	tide-laundary-powder-lemon-mint-110gmmrp-10-pack-12	Tide Laundary Powder Lemon & Mint 110gm(MRP-10) Pack-12	Tide Laundary Powder Lemon & Mint 110gm(MRP-10) Pack-12	DETHLDTID00000006	GF01048		1	5	2019-01-09 09:44:04.353985+00	2019-01-09 09:44:04.372121+00	t	81
364	Haldiram Masala Peanut 200 Gms mrp46	haldiram-masala-peanut-200-gms-mrp46	Haldiram Masala Peanut 200 Gms mrp46	Haldiram Masala Peanut 200 Gms mrp46	CNNSBFHAS00000023	GF01287	8.90406E+12	8	120	2019-01-09 04:45:25.769646+00	2019-01-09 04:45:25.786155+00	t	51
365	Haldiram nut cracker mrp5	haldiram-nut-cracker-mrp5	Haldiram nut cracker mrp5	Haldiram nut cracker mrp5	CNNSBFHAS00000024	GF01288		12	504	2019-01-09 04:45:25.80077+00	2019-01-09 04:45:25.816957+00	t	51
383	RIN BAR SAPPHIRE FW 150G+30G FREE	rin-bar-sapphire-fw-150g30g-free	RIN BAR SAPPHIRE FW 150G+30G FREE	RIN BAR SAPPHIRE FW 150G+30G FREE	DETHLDRIN00000004	GF01182		6	60	2019-01-09 09:44:04.387803+00	2019-01-09 09:44:04.404702+00	t	23
366	Haldiram nut cracker mrp10	haldiram-nut-cracker-mrp10	Haldiram nut cracker mrp10	Haldiram nut cracker mrp10	CNNSBFHAS00000025	GF01289	8.90406E+12	10	300	2019-01-09 04:45:25.832194+00	2019-01-09 04:45:25.849782+00	t	51
367	Haldiram Hing Channa MRP 10	haldiram-hing-channa-mrp-10	Haldiram Hing Channa MRP 10	Haldiram Hing Channa MRP 10	CNNSBFHAS00000026	GF01623	8.90406E+12	10	300	2019-01-09 04:45:25.866022+00	2019-01-09 04:45:25.882016+00	t	51
384	Tide Det Powder + Lemon 2kg  (MRP-204) Pack-12	tide-det-powder-lemon-2kg-mrp-204-pack-12	Tide Det Powder + Lemon 2kg  (MRP-204) Pack-12	Tide Det Powder + Lemon 2kg  (MRP-204) Pack-12	DETHLDTID00000007	GF01046_1		1	12	2019-01-09 09:44:04.420861+00	2019-01-09 09:44:04.438069+00	t	81
368	Haldiram Panchrattan MRP 10	haldiram-panchrattan-mrp-10	Haldiram Panchrattan MRP 10	Haldiram Panchrattan MRP 10	CNNSBFHAS00000027	GF01624	8.90406E+12	10	300	2019-01-09 04:45:25.897483+00	2019-01-09 04:45:25.913235+00	t	51
369	Haldiram Kaju Mixture MRP 10	haldiram-kaju-mixture-mrp-10	Haldiram Kaju Mixture MRP 10	Haldiram Kaju Mixture MRP 10	CNNSBFHAS00000028	GF01625	8.90406E+12	10	300	2019-01-09 04:45:25.928044+00	2019-01-09 04:45:25.944854+00	t	51
385	Tide Det Powder + Jasmine  1kg  (MRP-90) Pack-24	tide-det-powder-jasmine-1kg-mrp-90-pack-24	Tide Det Powder + Jasmine  1kg  (MRP-90) Pack-24	Tide Det Powder + Jasmine  1kg  (MRP-90) Pack-24	DETHLDTID00000008	GF01042_1		3	24	2019-01-09 09:44:04.454766+00	2019-01-09 09:44:04.471986+00	t	81
370	Haldiram All in One Mixture MRP 10	haldiram-all-in-one-mixture-mrp-10	Haldiram All in One Mixture MRP 10	Haldiram All in One Mixture MRP 10	CNNSBFHAS00000029	GF01626	8.90406E+12	10	300	2019-01-09 04:45:25.960174+00	2019-01-09 04:45:25.978791+00	t	51
371	Haldiram Diet Roasted Mixture MRP 10	haldiram-diet-roasted-mixture-mrp-10	Haldiram Diet Roasted Mixture MRP 10	Haldiram Diet Roasted Mixture MRP 10	CNNSBFHAS00000030	GF01627	8.90406E+12	10	300	2019-01-09 04:45:25.993476+00	2019-01-09 04:45:26.035616+00	t	51
386	VIM LIQUID POUCH 225 ML(MRP-40)	vim-liquid-pouch-225-mlmrp-40	VIM LIQUID POUCH 225 ML(MRP-40)	VIM LIQUID POUCH 225 ML(MRP-40)	DWSHLDVIM00000005	GF01619		6	36	2019-01-09 09:44:04.488829+00	2019-01-09 09:44:04.506746+00	t	60
372	Saffola Masala Oats Chinese - 39 gm (MRP-18)	saffola-masala-oats-chinese-39-gm-mrp-18	Saffola Masala Oats Chinese - 39 gm (MRP-18)	Saffola Masala Oats Chinese - 39 gm (MRP-18)	BFCSBFSOA00000001	GF00205	8.90109E+12	12	240	2019-01-09 04:45:26.051634+00	2019-01-09 04:45:26.067726+00	t	84
373	Saffola Masala Oats Classic Masala - 39 gm (MRP-15)	saffola-masala-oats-classic-masala-39-gm-mrp-15	Saffola Masala Oats Classic Masala - 39 gm (MRP-15)	Saffola Masala Oats Classic Masala - 39 gm (MRP-15)	BFCSBFSOA00000002	GF00206	8.90109E+12	12	240	2019-01-09 04:45:26.083933+00	2019-01-09 04:45:26.109073+00	t	84
387	VIM LIQUID Gel 155ML (MRP-20)	vim-liquid-gel-155ml-mrp-20	VIM LIQUID Gel 155ML (MRP-20)	VIM LIQUID Gel 155ML (MRP-20)	DWSHLDVIM00000006	GF01697		9	36	2019-01-09 09:44:04.523152+00	2019-01-09 09:44:04.540127+00	t	60
374	Saffola Masala Oats Italian - 39 gm (MRP-18)	saffola-masala-oats-italian-39-gm-mrp-18	Saffola Masala Oats Italian - 39 gm (MRP-18)	Saffola Masala Oats Italian - 39 gm (MRP-18)	BFCSBFSOA00000003	GF00208	8.90109E+12	12	240	2019-01-09 04:45:26.125189+00	2019-01-09 04:45:26.141108+00	t	84
375	Saffola Masala Oats Veggie Twist - 39 gm (MRP-15)	saffola-masala-oats-veggie-twist-39-gm-mrp-15	Saffola Masala Oats Veggie Twist - 39 gm (MRP-15)	Saffola Masala Oats Veggie Twist - 39 gm (MRP-15)	BFCSBFSOA00000004	GF00210	8.90109E+12	12	240	2019-01-09 04:45:26.155784+00	2019-01-09 04:45:26.171393+00	t	84
388	VIM LIQUID Gel 55ML (MRP-10)	vim-liquid-gel-55ml-mrp-10	VIM LIQUID Gel 55ML (MRP-10)	VIM LIQUID Gel 55ML (MRP-10)	DWSHLDVIM00000007	GF01698		12	48	2019-01-09 09:44:04.555528+00	2019-01-09 09:44:04.572363+00	t	60
376	Saffola Masala Oats Pongal - 39 gm (MRP-15)	saffola-masala-oats-pongal-39-gm-mrp-15	Saffola Masala Oats Pongal - 39 gm (MRP-15)	Saffola Masala Oats Pongal - 39 gm (MRP-15)	BFCSBFSOA00000005	GF00212	8.90109E+12	12	240	2019-01-09 04:45:26.185748+00	2019-01-09 04:45:26.201066+00	t	84
377	Saffola Tandoori Magic Masala Oats - 39 gm  (MRP-15)	saffola-tandoori-magic-masala-oats-39-gm-mrp-15	Saffola Tandoori Magic Masala Oats - 39 gm  (MRP-15)	Saffola Tandoori Magic Masala Oats - 39 gm  (MRP-15)	BFCSBFSOA00000006	GF00216	8.90109E+12	12	240	2019-01-09 04:45:26.216083+00	2019-01-09 04:45:26.231846+00	t	84
378	Saffola Tandoori Magic Masala Oats - 39 gm  (MRP-18)	saffola-tandoori-magic-masala-oats-39-gm-mrp-18	Saffola Tandoori Magic Masala Oats - 39 gm  (MRP-18)	Saffola Tandoori Magic Masala Oats - 39 gm  (MRP-18)	BFCSBFSOA00000007	GF00216_1		12	240	2019-01-09 04:45:26.246683+00	2019-01-09 04:45:26.262522+00	t	84
379	Saffola Tangy Chaat Masala Oats - 39 gm (MRP-15)	saffola-tangy-chaat-masala-oats-39-gm-mrp-15	Saffola Tangy Chaat Masala Oats - 39 gm (MRP-15)	Saffola Tangy Chaat Masala Oats - 39 gm (MRP-15)	BFCSBFSOA00000008	GF00217	8.90109E+12	12	240	2019-01-09 04:45:26.278241+00	2019-01-09 04:45:26.294821+00	t	84
380	Saffola Oats - 400 gm  (MRP-77)	saffola-oats-400-gm-mrp-77	Saffola Oats - 400 gm  (MRP-77)	Saffola Oats - 400 gm  (MRP-77)	BFCSBFSOA00000009	GF00215	8.90109E+12	12	60	2019-01-09 04:45:26.309068+00	2019-01-09 04:45:26.325299+00	t	84
\.


--
-- Data for Name: products_productcategory; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productcategory (id, created_at, modified_at, status, category_id, product_id) FROM stdin;
28	2019-01-08 08:24:54.459054+00	2019-01-08 08:24:54.459069+00	t	15	28
29	2019-01-08 08:24:54.491307+00	2019-01-08 08:24:54.491322+00	t	15	29
30	2019-01-08 08:24:54.523008+00	2019-01-08 08:24:54.523025+00	t	15	30
31	2019-01-08 08:24:54.554426+00	2019-01-08 08:24:54.554441+00	t	15	31
32	2019-01-08 08:24:54.586002+00	2019-01-08 08:24:54.586017+00	t	15	32
33	2019-01-08 08:24:54.616742+00	2019-01-08 08:24:54.616759+00	t	15	33
34	2019-01-08 08:24:54.648149+00	2019-01-08 08:24:54.648164+00	t	15	34
35	2019-01-08 08:24:54.679857+00	2019-01-08 08:24:54.679872+00	t	15	35
36	2019-01-08 08:24:54.71122+00	2019-01-08 08:24:54.711235+00	t	15	36
37	2019-01-08 08:24:54.741105+00	2019-01-08 08:24:54.74112+00	t	15	37
38	2019-01-08 08:24:54.771633+00	2019-01-08 08:24:54.771648+00	t	15	38
39	2019-01-08 08:24:54.802289+00	2019-01-08 08:24:54.802305+00	t	15	39
40	2019-01-08 08:24:54.838567+00	2019-01-08 08:24:54.838583+00	t	15	40
41	2019-01-08 14:12:04.049488+00	2019-01-08 14:12:04.049509+00	t	3	41
42	2019-01-08 14:12:04.088526+00	2019-01-08 14:12:04.088546+00	t	3	42
43	2019-01-08 14:12:04.122778+00	2019-01-08 14:12:04.122793+00	t	4	43
44	2019-01-08 14:12:04.161743+00	2019-01-08 14:12:04.161771+00	t	5	44
45	2019-01-08 14:12:04.195318+00	2019-01-08 14:12:04.195337+00	t	5	45
46	2019-01-08 14:12:04.234695+00	2019-01-08 14:12:04.234716+00	t	5	46
47	2019-01-08 14:12:04.268737+00	2019-01-08 14:12:04.268754+00	t	5	47
48	2019-01-08 14:12:04.306763+00	2019-01-08 14:12:04.306779+00	t	5	48
49	2019-01-08 14:12:04.341237+00	2019-01-08 14:12:04.341252+00	t	5	49
50	2019-01-08 14:12:04.374504+00	2019-01-08 14:12:04.374519+00	t	5	50
51	2019-01-08 14:12:04.408136+00	2019-01-08 14:12:04.408151+00	t	5	51
52	2019-01-08 14:12:04.444796+00	2019-01-08 14:12:04.444812+00	t	5	52
53	2019-01-08 14:12:04.478274+00	2019-01-08 14:12:04.478291+00	t	5	53
54	2019-01-08 14:12:04.512985+00	2019-01-08 14:12:04.513006+00	t	5	54
55	2019-01-08 14:12:04.547031+00	2019-01-08 14:12:04.547047+00	t	5	55
56	2019-01-08 14:12:04.579191+00	2019-01-08 14:12:04.579207+00	t	6	56
57	2019-01-08 14:12:04.611746+00	2019-01-08 14:12:04.611763+00	t	6	57
58	2019-01-08 14:12:04.643933+00	2019-01-08 14:12:04.643952+00	t	4	58
59	2019-01-08 14:12:04.677615+00	2019-01-08 14:12:04.677633+00	t	4	59
60	2019-01-08 14:12:04.711073+00	2019-01-08 14:12:04.711089+00	t	4	60
61	2019-01-08 14:12:04.745047+00	2019-01-08 14:12:04.745063+00	t	5	61
62	2019-01-08 14:12:04.778061+00	2019-01-08 14:12:04.778079+00	t	5	62
63	2019-01-08 14:12:04.811275+00	2019-01-08 14:12:04.811294+00	t	5	63
64	2019-01-08 14:12:04.850849+00	2019-01-08 14:12:04.850867+00	t	7	64
65	2019-01-08 14:12:04.888127+00	2019-01-08 14:12:04.888154+00	t	8	65
66	2019-01-08 14:12:04.92276+00	2019-01-08 14:12:04.922779+00	t	8	66
67	2019-01-08 14:12:04.955936+00	2019-01-08 14:12:04.955954+00	t	8	67
68	2019-01-08 14:12:04.987951+00	2019-01-08 14:12:04.987968+00	t	9	68
69	2019-01-08 14:12:05.05432+00	2019-01-08 14:12:05.054336+00	t	9	69
70	2019-01-08 14:12:05.089528+00	2019-01-08 14:12:05.089551+00	t	8	70
71	2019-01-08 14:12:05.121806+00	2019-01-08 14:12:05.121822+00	t	8	71
72	2019-01-08 14:12:05.155114+00	2019-01-08 14:12:05.155129+00	t	8	72
73	2019-01-08 14:12:05.187481+00	2019-01-08 14:12:05.187497+00	t	8	73
74	2019-01-08 14:12:05.221493+00	2019-01-08 14:12:05.22151+00	t	7	74
75	2019-01-08 14:12:05.255507+00	2019-01-08 14:12:05.255526+00	t	7	75
76	2019-01-08 14:12:05.288926+00	2019-01-08 14:12:05.288941+00	t	7	76
77	2019-01-08 14:12:05.323013+00	2019-01-08 14:12:05.323031+00	t	10	77
78	2019-01-08 14:12:05.356386+00	2019-01-08 14:12:05.356402+00	t	10	78
79	2019-01-08 14:12:05.396686+00	2019-01-08 14:12:05.396702+00	t	7	79
80	2019-01-08 14:12:05.433161+00	2019-01-08 14:12:05.433175+00	t	8	80
81	2019-01-08 14:12:05.466165+00	2019-01-08 14:12:05.466184+00	t	7	81
82	2019-01-08 14:12:05.498105+00	2019-01-08 14:12:05.498121+00	t	10	82
83	2019-01-08 14:12:05.530006+00	2019-01-08 14:12:05.530024+00	t	10	83
84	2019-01-08 14:12:05.562521+00	2019-01-08 14:12:05.562539+00	t	7	84
85	2019-01-08 14:12:05.594954+00	2019-01-08 14:12:05.59497+00	t	8	85
86	2019-01-08 14:12:05.630049+00	2019-01-08 14:12:05.63008+00	t	8	86
87	2019-01-08 14:12:05.664132+00	2019-01-08 14:12:05.664148+00	t	8	87
88	2019-01-08 14:12:05.699331+00	2019-01-08 14:12:05.699346+00	t	8	88
89	2019-01-08 14:12:05.733774+00	2019-01-08 14:12:05.733793+00	t	8	89
90	2019-01-08 14:12:05.771352+00	2019-01-08 14:12:05.77137+00	t	8	90
91	2019-01-08 14:12:05.808676+00	2019-01-08 14:12:05.808695+00	t	7	91
92	2019-01-08 14:12:05.84285+00	2019-01-08 14:12:05.842865+00	t	8	92
93	2019-01-08 14:12:05.875212+00	2019-01-08 14:12:05.875229+00	t	4	93
94	2019-01-08 14:12:05.907146+00	2019-01-08 14:12:05.907162+00	t	4	94
95	2019-01-08 14:12:05.939462+00	2019-01-08 14:12:05.939476+00	t	4	95
96	2019-01-08 14:12:05.973062+00	2019-01-08 14:12:05.973077+00	t	4	96
97	2019-01-08 14:12:06.010554+00	2019-01-08 14:12:06.010574+00	t	4	97
98	2019-01-08 14:12:06.046312+00	2019-01-08 14:12:06.046336+00	t	11	98
99	2019-01-08 14:12:06.079798+00	2019-01-08 14:12:06.079816+00	t	11	99
100	2019-01-08 14:12:06.113915+00	2019-01-08 14:12:06.113931+00	t	11	100
101	2019-01-08 14:12:06.146802+00	2019-01-08 14:12:06.14683+00	t	12	101
102	2019-01-08 14:12:06.179248+00	2019-01-08 14:12:06.179263+00	t	12	102
103	2019-01-08 14:12:06.211233+00	2019-01-08 14:12:06.211248+00	t	12	103
104	2019-01-08 14:12:06.243368+00	2019-01-08 14:12:06.243383+00	t	13	104
105	2019-01-08 14:12:06.275711+00	2019-01-08 14:12:06.275727+00	t	13	105
106	2019-01-08 14:12:06.30843+00	2019-01-08 14:12:06.308446+00	t	13	106
107	2019-01-08 14:12:06.342201+00	2019-01-08 14:12:06.342221+00	t	13	107
108	2019-01-08 14:12:06.375782+00	2019-01-08 14:12:06.3758+00	t	13	108
109	2019-01-08 14:12:06.408888+00	2019-01-08 14:12:06.408904+00	t	13	109
110	2019-01-08 14:12:06.441635+00	2019-01-08 14:12:06.441651+00	t	13	110
111	2019-01-08 14:12:06.474023+00	2019-01-08 14:12:06.47404+00	t	13	111
112	2019-01-08 14:12:06.507872+00	2019-01-08 14:12:06.507887+00	t	13	112
113	2019-01-08 14:12:06.539495+00	2019-01-08 14:12:06.539519+00	t	9	113
114	2019-01-08 14:12:06.571754+00	2019-01-08 14:12:06.57177+00	t	9	114
115	2019-01-08 14:12:06.60276+00	2019-01-08 14:12:06.602777+00	t	4	115
116	2019-01-08 14:12:06.634084+00	2019-01-08 14:12:06.634101+00	t	4	116
117	2019-01-08 14:12:06.665606+00	2019-01-08 14:12:06.665622+00	t	4	117
118	2019-01-08 14:12:06.701127+00	2019-01-08 14:12:06.701148+00	t	4	118
119	2019-01-08 14:12:06.740496+00	2019-01-08 14:12:06.740514+00	t	13	119
120	2019-01-08 14:12:06.772459+00	2019-01-08 14:12:06.772478+00	t	13	120
121	2019-01-08 14:12:06.803841+00	2019-01-08 14:12:06.803857+00	t	13	121
122	2019-01-08 14:12:06.836053+00	2019-01-08 14:12:06.836073+00	t	8	122
123	2019-01-08 14:12:06.868879+00	2019-01-08 14:12:06.868894+00	t	8	123
124	2019-01-08 14:12:06.900696+00	2019-01-08 14:12:06.900717+00	t	8	124
125	2019-01-08 14:12:06.932996+00	2019-01-08 14:12:06.933013+00	t	8	125
126	2019-01-08 14:12:06.964596+00	2019-01-08 14:12:06.964618+00	t	8	126
127	2019-01-08 14:12:06.996541+00	2019-01-08 14:12:06.996558+00	t	8	127
128	2019-01-08 14:12:07.028589+00	2019-01-08 14:12:07.028605+00	t	8	128
129	2019-01-08 14:12:07.060319+00	2019-01-08 14:12:07.060337+00	t	8	129
130	2019-01-08 14:12:07.092143+00	2019-01-08 14:12:07.092161+00	t	8	130
131	2019-01-08 14:12:07.124322+00	2019-01-08 14:12:07.124338+00	t	8	131
132	2019-01-08 14:12:07.156055+00	2019-01-08 14:12:07.15607+00	t	8	132
133	2019-01-08 14:12:07.187733+00	2019-01-08 14:12:07.18775+00	t	8	133
134	2019-01-08 14:12:07.221222+00	2019-01-08 14:12:07.221238+00	t	8	134
135	2019-01-08 14:12:07.25332+00	2019-01-08 14:12:07.253336+00	t	8	135
136	2019-01-08 14:12:07.285496+00	2019-01-08 14:12:07.285512+00	t	8	136
137	2019-01-08 14:12:07.316948+00	2019-01-08 14:12:07.316965+00	t	8	137
138	2019-01-08 14:12:07.34951+00	2019-01-08 14:12:07.349526+00	t	8	138
139	2019-01-08 14:12:07.381895+00	2019-01-08 14:12:07.381916+00	t	4	139
140	2019-01-08 14:12:07.413542+00	2019-01-08 14:12:07.413566+00	t	4	140
141	2019-01-08 14:12:07.446671+00	2019-01-08 14:12:07.446687+00	t	4	141
142	2019-01-08 14:12:07.477612+00	2019-01-08 14:12:07.477627+00	t	14	142
143	2019-01-08 14:12:07.509797+00	2019-01-08 14:12:07.509816+00	t	4	143
144	2019-01-08 14:12:07.543178+00	2019-01-08 14:12:07.543196+00	t	4	144
145	2019-01-08 14:12:07.575047+00	2019-01-08 14:12:07.575066+00	t	4	145
146	2019-01-08 14:12:07.60755+00	2019-01-08 14:12:07.607571+00	t	4	146
147	2019-01-08 14:12:07.639922+00	2019-01-08 14:12:07.639944+00	t	4	147
148	2019-01-08 14:12:07.672396+00	2019-01-08 14:12:07.672418+00	t	4	148
149	2019-01-08 14:12:07.704736+00	2019-01-08 14:12:07.704751+00	t	4	149
150	2019-01-08 14:12:07.736124+00	2019-01-08 14:12:07.736139+00	t	4	150
151	2019-01-08 14:12:07.767762+00	2019-01-08 14:12:07.767779+00	t	13	151
152	2019-01-08 14:12:07.800953+00	2019-01-08 14:12:07.80097+00	t	13	152
153	2019-01-08 14:12:07.832719+00	2019-01-08 14:12:07.832735+00	t	5	153
154	2019-01-08 14:12:07.865306+00	2019-01-08 14:12:07.865331+00	t	8	154
155	2019-01-08 14:12:07.89743+00	2019-01-08 14:12:07.897446+00	t	15	155
156	2019-01-08 14:12:07.929411+00	2019-01-08 14:12:07.929429+00	t	15	156
157	2019-01-08 14:12:07.961128+00	2019-01-08 14:12:07.961144+00	t	15	157
158	2019-01-08 14:12:07.992181+00	2019-01-08 14:12:07.992199+00	t	15	158
159	2019-01-08 14:12:08.02782+00	2019-01-08 14:12:08.027839+00	t	15	159
160	2019-01-08 14:12:08.060303+00	2019-01-08 14:12:08.060319+00	t	15	160
161	2019-01-08 14:12:08.093211+00	2019-01-08 14:12:08.093241+00	t	15	161
162	2019-01-08 14:12:08.126459+00	2019-01-08 14:12:08.126477+00	t	15	162
163	2019-01-08 14:12:08.160013+00	2019-01-08 14:12:08.160034+00	t	15	163
164	2019-01-08 14:12:08.192188+00	2019-01-08 14:12:08.192214+00	t	15	164
165	2019-01-08 14:12:08.225174+00	2019-01-08 14:12:08.225192+00	t	15	165
166	2019-01-08 14:12:08.258126+00	2019-01-08 14:12:08.258141+00	t	15	166
167	2019-01-08 14:12:08.290822+00	2019-01-08 14:12:08.290837+00	t	15	167
168	2019-01-08 14:12:08.323204+00	2019-01-08 14:12:08.323232+00	t	15	168
169	2019-01-08 14:12:08.357097+00	2019-01-08 14:12:08.357124+00	t	8	169
170	2019-01-08 14:12:08.389749+00	2019-01-08 14:12:08.389769+00	t	8	170
171	2019-01-08 14:12:08.421455+00	2019-01-08 14:12:08.421471+00	t	5	171
172	2019-01-08 14:12:08.452816+00	2019-01-08 14:12:08.452837+00	t	16	172
173	2019-01-08 14:12:08.492673+00	2019-01-08 14:12:08.492693+00	t	16	173
174	2019-01-08 14:12:08.52547+00	2019-01-08 14:12:08.525492+00	t	16	174
175	2019-01-08 14:12:08.558524+00	2019-01-08 14:12:08.558546+00	t	16	175
176	2019-01-08 14:12:08.592182+00	2019-01-08 14:12:08.592202+00	t	4	176
177	2019-01-08 14:12:08.626563+00	2019-01-08 14:12:08.626582+00	t	4	177
178	2019-01-08 14:12:08.660129+00	2019-01-08 14:12:08.660145+00	t	10	178
179	2019-01-08 14:12:08.693667+00	2019-01-08 14:12:08.693689+00	t	10	179
180	2019-01-08 14:12:08.725561+00	2019-01-08 14:12:08.725586+00	t	17	180
181	2019-01-08 14:12:08.757597+00	2019-01-08 14:12:08.757613+00	t	17	181
182	2019-01-08 14:12:08.789299+00	2019-01-08 14:12:08.789314+00	t	17	182
183	2019-01-08 14:12:08.820105+00	2019-01-08 14:12:08.820125+00	t	17	183
184	2019-01-08 14:12:08.854247+00	2019-01-08 14:12:08.854262+00	t	17	184
185	2019-01-08 14:12:08.886378+00	2019-01-08 14:12:08.886393+00	t	17	185
186	2019-01-08 14:12:08.918282+00	2019-01-08 14:12:08.918304+00	t	18	186
187	2019-01-08 14:12:08.951242+00	2019-01-08 14:12:08.951261+00	t	18	187
188	2019-01-08 14:12:08.982478+00	2019-01-08 14:12:08.982494+00	t	18	188
189	2019-01-08 14:12:09.017859+00	2019-01-08 14:12:09.017888+00	t	18	189
190	2019-01-08 14:12:09.050857+00	2019-01-08 14:12:09.050873+00	t	18	190
191	2019-01-08 14:12:09.082884+00	2019-01-08 14:12:09.082905+00	t	4	191
192	2019-01-08 14:12:09.116053+00	2019-01-08 14:12:09.116075+00	t	4	192
193	2019-01-08 14:12:09.149422+00	2019-01-08 14:12:09.149444+00	t	4	193
194	2019-01-08 14:12:09.181573+00	2019-01-08 14:12:09.181592+00	t	4	194
195	2019-01-08 14:12:09.213572+00	2019-01-08 14:12:09.213589+00	t	4	195
196	2019-01-08 14:12:09.244571+00	2019-01-08 14:12:09.244594+00	t	4	196
197	2019-01-08 14:12:09.276981+00	2019-01-08 14:12:09.276998+00	t	4	197
198	2019-01-08 14:12:09.308444+00	2019-01-08 14:12:09.308463+00	t	4	198
199	2019-01-08 14:12:09.340374+00	2019-01-08 14:12:09.340389+00	t	4	199
200	2019-01-08 14:12:09.372129+00	2019-01-08 14:12:09.372146+00	t	4	200
201	2019-01-08 14:12:09.405999+00	2019-01-08 14:12:09.406017+00	t	4	201
202	2019-01-08 14:12:09.43762+00	2019-01-08 14:12:09.437636+00	t	13	202
203	2019-01-08 14:12:09.469285+00	2019-01-08 14:12:09.469303+00	t	8	203
204	2019-01-08 14:12:09.50066+00	2019-01-08 14:12:09.500676+00	t	8	204
205	2019-01-08 14:12:09.531353+00	2019-01-08 14:12:09.531375+00	t	4	205
206	2019-01-08 14:12:09.564812+00	2019-01-08 14:12:09.56483+00	t	13	206
207	2019-01-08 14:12:09.596965+00	2019-01-08 14:12:09.596991+00	t	13	207
208	2019-01-08 14:12:09.629757+00	2019-01-08 14:12:09.629774+00	t	13	208
209	2019-01-08 14:12:09.662237+00	2019-01-08 14:12:09.662261+00	t	5	209
210	2019-01-08 14:12:09.694445+00	2019-01-08 14:12:09.694476+00	t	13	210
211	2019-01-08 14:12:09.727224+00	2019-01-08 14:12:09.727248+00	t	12	211
212	2019-01-08 14:12:09.759309+00	2019-01-08 14:12:09.759326+00	t	12	212
213	2019-01-08 14:12:09.79044+00	2019-01-08 14:12:09.790461+00	t	5	213
214	2019-01-08 14:12:09.823289+00	2019-01-08 14:12:09.823313+00	t	12	214
215	2019-01-08 14:12:09.872782+00	2019-01-08 14:12:09.87281+00	t	13	215
216	2019-01-08 14:12:09.904689+00	2019-01-08 14:12:09.904711+00	t	13	216
217	2019-01-08 14:12:09.938573+00	2019-01-08 14:12:09.938598+00	t	13	217
218	2019-01-08 14:12:09.970695+00	2019-01-08 14:12:09.970711+00	t	13	218
219	2019-01-08 14:12:10.068022+00	2019-01-08 14:12:10.068054+00	t	13	219
220	2019-01-08 14:12:10.100847+00	2019-01-08 14:12:10.100864+00	t	13	220
221	2019-01-08 14:12:10.133238+00	2019-01-08 14:12:10.133256+00	t	13	221
222	2019-01-08 14:12:10.167665+00	2019-01-08 14:12:10.16769+00	t	13	222
223	2019-01-08 14:12:10.204034+00	2019-01-08 14:12:10.204059+00	t	4	223
224	2019-01-08 14:12:10.237264+00	2019-01-08 14:12:10.237288+00	t	4	224
225	2019-01-08 14:12:10.270325+00	2019-01-08 14:12:10.270348+00	t	4	225
226	2019-01-08 14:12:10.302586+00	2019-01-08 14:12:10.302602+00	t	4	226
227	2019-01-08 14:12:10.33795+00	2019-01-08 14:12:10.337968+00	t	4	227
228	2019-01-08 14:12:10.372862+00	2019-01-08 14:12:10.37288+00	t	4	228
229	2019-01-08 14:12:10.413716+00	2019-01-08 14:12:10.413734+00	t	4	229
230	2019-01-08 14:12:10.449867+00	2019-01-08 14:12:10.449885+00	t	4	230
231	2019-01-08 14:12:10.483928+00	2019-01-08 14:12:10.483946+00	t	4	231
232	2019-01-08 14:12:10.520231+00	2019-01-08 14:12:10.520254+00	t	4	232
233	2019-01-08 14:12:10.557992+00	2019-01-08 14:12:10.558008+00	t	4	233
234	2019-01-08 14:12:10.592545+00	2019-01-08 14:12:10.592564+00	t	13	234
235	2019-01-08 14:12:10.626829+00	2019-01-08 14:12:10.626848+00	t	13	235
236	2019-01-08 14:12:10.661784+00	2019-01-08 14:12:10.661802+00	t	13	236
237	2019-01-08 14:12:10.69614+00	2019-01-08 14:12:10.696157+00	t	13	237
238	2019-01-08 14:12:10.72891+00	2019-01-08 14:12:10.728928+00	t	13	238
239	2019-01-08 14:12:10.761711+00	2019-01-08 14:12:10.761734+00	t	13	239
240	2019-01-08 14:12:10.794402+00	2019-01-08 14:12:10.794422+00	t	13	240
241	2019-01-08 14:12:10.826733+00	2019-01-08 14:12:10.826752+00	t	13	241
242	2019-01-08 14:12:10.865289+00	2019-01-08 14:12:10.865309+00	t	13	242
243	2019-01-08 14:12:10.899479+00	2019-01-08 14:12:10.899499+00	t	4	243
244	2019-01-08 14:12:10.932432+00	2019-01-08 14:12:10.932446+00	t	4	244
245	2019-01-08 14:12:10.966935+00	2019-01-08 14:12:10.966952+00	t	4	245
246	2019-01-08 14:12:11.002764+00	2019-01-08 14:12:11.002779+00	t	13	246
247	2019-01-08 14:12:11.036555+00	2019-01-08 14:12:11.036575+00	t	12	247
248	2019-01-08 14:12:11.071484+00	2019-01-08 14:12:11.0715+00	t	19	248
249	2019-01-08 14:12:11.105284+00	2019-01-08 14:12:11.105309+00	t	19	249
250	2019-01-08 14:12:11.138289+00	2019-01-08 14:12:11.13831+00	t	19	250
251	2019-01-08 14:12:11.171206+00	2019-01-08 14:12:11.171221+00	t	19	251
252	2019-01-08 14:12:11.203534+00	2019-01-08 14:12:11.203552+00	t	19	252
253	2019-01-08 14:12:11.236739+00	2019-01-08 14:12:11.236757+00	t	19	253
254	2019-01-08 14:12:11.273142+00	2019-01-08 14:12:11.273157+00	t	19	254
255	2019-01-08 14:12:11.310782+00	2019-01-08 14:12:11.310797+00	t	19	255
256	2019-01-08 14:12:11.343934+00	2019-01-08 14:12:11.343951+00	t	16	256
257	2019-01-08 14:12:11.376768+00	2019-01-08 14:12:11.376788+00	t	10	257
258	2019-01-08 14:12:11.410498+00	2019-01-08 14:12:11.410522+00	t	10	258
259	2019-01-08 14:12:11.442174+00	2019-01-08 14:12:11.442194+00	t	10	259
260	2019-01-08 14:12:11.47497+00	2019-01-08 14:12:11.474989+00	t	10	260
261	2019-01-08 14:12:11.508194+00	2019-01-08 14:12:11.508218+00	t	8	261
262	2019-01-08 14:12:11.541458+00	2019-01-08 14:12:11.541474+00	t	13	262
263	2019-01-08 14:12:11.573404+00	2019-01-08 14:12:11.573423+00	t	13	263
264	2019-01-08 14:12:11.60515+00	2019-01-08 14:12:11.605165+00	t	20	264
265	2019-01-08 14:12:11.638444+00	2019-01-08 14:12:11.638461+00	t	20	265
266	2019-01-08 14:12:11.670773+00	2019-01-08 14:12:11.670788+00	t	20	266
267	2019-01-08 14:12:11.702796+00	2019-01-08 14:12:11.702813+00	t	12	267
268	2019-01-08 14:12:11.734716+00	2019-01-08 14:12:11.734734+00	t	13	268
269	2019-01-08 14:12:11.766649+00	2019-01-08 14:12:11.766667+00	t	13	269
270	2019-01-09 04:45:22.608726+00	2019-01-09 04:45:22.608744+00	t	22	270
271	2019-01-09 04:45:22.647176+00	2019-01-09 04:45:22.647192+00	t	23	271
272	2019-01-09 04:45:22.682134+00	2019-01-09 04:45:22.682155+00	t	25	272
273	2019-01-09 04:45:22.714409+00	2019-01-09 04:45:22.714424+00	t	27	273
274	2019-01-09 04:45:22.752686+00	2019-01-09 04:45:22.752711+00	t	27	274
275	2019-01-09 04:45:22.785011+00	2019-01-09 04:45:22.785025+00	t	27	275
276	2019-01-09 04:45:22.815736+00	2019-01-09 04:45:22.81575+00	t	22	276
277	2019-01-09 04:45:22.853615+00	2019-01-09 04:45:22.85363+00	t	22	277
278	2019-01-09 04:45:22.886437+00	2019-01-09 04:45:22.886453+00	t	22	278
279	2019-01-09 04:45:22.921107+00	2019-01-09 04:45:22.92113+00	t	27	279
280	2019-01-09 04:45:22.951257+00	2019-01-09 04:45:22.951272+00	t	27	280
281	2019-01-09 04:45:22.986146+00	2019-01-09 04:45:22.98616+00	t	27	281
282	2019-01-09 04:45:23.019557+00	2019-01-09 04:45:23.019573+00	t	27	282
283	2019-01-09 04:45:23.051473+00	2019-01-09 04:45:23.051488+00	t	27	283
284	2019-01-09 04:45:23.086597+00	2019-01-09 04:45:23.086611+00	t	27	284
285	2019-01-09 04:45:23.119402+00	2019-01-09 04:45:23.119416+00	t	23	285
286	2019-01-09 04:45:23.153021+00	2019-01-09 04:45:23.153035+00	t	28	286
287	2019-01-09 04:45:23.189118+00	2019-01-09 04:45:23.189133+00	t	28	287
288	2019-01-09 04:45:23.220205+00	2019-01-09 04:45:23.22022+00	t	29	288
289	2019-01-09 04:45:23.256221+00	2019-01-09 04:45:23.256239+00	t	29	289
290	2019-01-09 04:45:23.288534+00	2019-01-09 04:45:23.288548+00	t	29	290
291	2019-01-09 04:45:23.320697+00	2019-01-09 04:45:23.320711+00	t	28	291
292	2019-01-09 04:45:23.350477+00	2019-01-09 04:45:23.350491+00	t	22	292
293	2019-01-09 04:45:23.3899+00	2019-01-09 04:45:23.389914+00	t	28	293
294	2019-01-09 04:45:23.420814+00	2019-01-09 04:45:23.420828+00	t	28	294
295	2019-01-09 04:45:23.451609+00	2019-01-09 04:45:23.451623+00	t	28	295
296	2019-01-09 04:45:23.484932+00	2019-01-09 04:45:23.484947+00	t	28	296
297	2019-01-09 04:45:23.519662+00	2019-01-09 04:45:23.519682+00	t	22	297
298	2019-01-09 04:45:23.551379+00	2019-01-09 04:45:23.551393+00	t	28	298
299	2019-01-09 04:45:23.583585+00	2019-01-09 04:45:23.583602+00	t	28	299
300	2019-01-09 04:45:23.615537+00	2019-01-09 04:45:23.615551+00	t	28	300
301	2019-01-09 04:45:23.646331+00	2019-01-09 04:45:23.646345+00	t	28	301
302	2019-01-09 04:45:23.677656+00	2019-01-09 04:45:23.677677+00	t	28	302
303	2019-01-09 04:45:23.708622+00	2019-01-09 04:45:23.708644+00	t	28	303
304	2019-01-09 04:45:23.739184+00	2019-01-09 04:45:23.739198+00	t	28	304
305	2019-01-09 04:45:23.770244+00	2019-01-09 04:45:23.770259+00	t	28	305
306	2019-01-09 04:45:23.800531+00	2019-01-09 04:45:23.800545+00	t	28	306
307	2019-01-09 04:45:23.834079+00	2019-01-09 04:45:23.834095+00	t	28	307
308	2019-01-09 04:45:23.86597+00	2019-01-09 04:45:23.865985+00	t	28	308
309	2019-01-09 04:45:23.896756+00	2019-01-09 04:45:23.896771+00	t	29	309
310	2019-01-09 04:45:23.929361+00	2019-01-09 04:45:23.929378+00	t	29	310
311	2019-01-09 04:45:23.963436+00	2019-01-09 04:45:23.96345+00	t	29	311
312	2019-01-09 04:45:23.996476+00	2019-01-09 04:45:23.99649+00	t	29	312
313	2019-01-09 04:45:24.030881+00	2019-01-09 04:45:24.030897+00	t	29	313
314	2019-01-09 04:45:24.068456+00	2019-01-09 04:45:24.068473+00	t	29	314
315	2019-01-09 04:45:24.104422+00	2019-01-09 04:45:24.104437+00	t	29	315
316	2019-01-09 04:45:24.134888+00	2019-01-09 04:45:24.134902+00	t	29	316
317	2019-01-09 04:45:24.167612+00	2019-01-09 04:45:24.167626+00	t	30	317
318	2019-01-09 04:45:24.198484+00	2019-01-09 04:45:24.198503+00	t	30	318
319	2019-01-09 04:45:24.233656+00	2019-01-09 04:45:24.233671+00	t	30	319
320	2019-01-09 04:45:24.265558+00	2019-01-09 04:45:24.265574+00	t	30	320
321	2019-01-09 04:45:24.301859+00	2019-01-09 04:45:24.301875+00	t	30	321
322	2019-01-09 04:45:24.33337+00	2019-01-09 04:45:24.333385+00	t	30	322
323	2019-01-09 04:45:24.364948+00	2019-01-09 04:45:24.364966+00	t	30	323
324	2019-01-09 04:45:24.40173+00	2019-01-09 04:45:24.401746+00	t	30	324
325	2019-01-09 04:45:24.432991+00	2019-01-09 04:45:24.433007+00	t	30	325
326	2019-01-09 04:45:24.46546+00	2019-01-09 04:45:24.465476+00	t	30	326
327	2019-01-09 04:45:24.49897+00	2019-01-09 04:45:24.498987+00	t	30	327
328	2019-01-09 04:45:24.529979+00	2019-01-09 04:45:24.529996+00	t	30	328
329	2019-01-09 04:45:24.561926+00	2019-01-09 04:45:24.561941+00	t	30	329
330	2019-01-09 04:45:24.592176+00	2019-01-09 04:45:24.592191+00	t	29	330
331	2019-01-09 04:45:24.62349+00	2019-01-09 04:45:24.623505+00	t	29	331
332	2019-01-09 04:45:24.654134+00	2019-01-09 04:45:24.654149+00	t	29	332
333	2019-01-09 04:45:24.685208+00	2019-01-09 04:45:24.685223+00	t	29	333
334	2019-01-09 04:45:24.718272+00	2019-01-09 04:45:24.718292+00	t	29	334
335	2019-01-09 04:45:24.752065+00	2019-01-09 04:45:24.752085+00	t	29	335
336	2019-01-09 04:45:24.783005+00	2019-01-09 04:45:24.78302+00	t	29	336
337	2019-01-09 04:45:24.819161+00	2019-01-09 04:45:24.819176+00	t	29	337
338	2019-01-09 04:45:24.865906+00	2019-01-09 04:45:24.865921+00	t	29	338
339	2019-01-09 04:45:24.896683+00	2019-01-09 04:45:24.896699+00	t	29	339
340	2019-01-09 04:45:24.932967+00	2019-01-09 04:45:24.932986+00	t	29	340
341	2019-01-09 04:45:24.968622+00	2019-01-09 04:45:24.968637+00	t	30	341
342	2019-01-09 04:45:25.04145+00	2019-01-09 04:45:25.041482+00	t	29	342
343	2019-01-09 04:45:25.0748+00	2019-01-09 04:45:25.074821+00	t	29	343
344	2019-01-09 04:45:25.11408+00	2019-01-09 04:45:25.114104+00	t	29	344
345	2019-01-09 04:45:25.146024+00	2019-01-09 04:45:25.146051+00	t	29	345
346	2019-01-09 04:45:25.18412+00	2019-01-09 04:45:25.184139+00	t	29	346
347	2019-01-09 04:45:25.216714+00	2019-01-09 04:45:25.216729+00	t	29	347
348	2019-01-09 04:45:25.24797+00	2019-01-09 04:45:25.247986+00	t	29	348
349	2019-01-09 04:45:25.282531+00	2019-01-09 04:45:25.282552+00	t	29	349
350	2019-01-09 04:45:25.314786+00	2019-01-09 04:45:25.314801+00	t	29	350
351	2019-01-09 04:45:25.348093+00	2019-01-09 04:45:25.348109+00	t	29	351
352	2019-01-09 04:45:25.377867+00	2019-01-09 04:45:25.377885+00	t	29	352
353	2019-01-09 04:45:25.417382+00	2019-01-09 04:45:25.417398+00	t	29	353
354	2019-01-09 04:45:25.458943+00	2019-01-09 04:45:25.458958+00	t	29	354
355	2019-01-09 04:45:25.491362+00	2019-01-09 04:45:25.491377+00	t	29	355
356	2019-01-09 04:45:25.528288+00	2019-01-09 04:45:25.52831+00	t	29	356
357	2019-01-09 04:45:25.560203+00	2019-01-09 04:45:25.560217+00	t	29	357
358	2019-01-09 04:45:25.593442+00	2019-01-09 04:45:25.593457+00	t	29	358
359	2019-01-09 04:45:25.627677+00	2019-01-09 04:45:25.627692+00	t	29	359
360	2019-01-09 04:45:25.661453+00	2019-01-09 04:45:25.661471+00	t	29	360
361	2019-01-09 04:45:25.693467+00	2019-01-09 04:45:25.693482+00	t	29	361
362	2019-01-09 04:45:25.726409+00	2019-01-09 04:45:25.726425+00	t	29	362
363	2019-01-09 04:45:25.757635+00	2019-01-09 04:45:25.75765+00	t	29	363
364	2019-01-09 04:45:25.790138+00	2019-01-09 04:45:25.790158+00	t	29	364
365	2019-01-09 04:45:25.821017+00	2019-01-09 04:45:25.821033+00	t	29	365
366	2019-01-09 04:45:25.8537+00	2019-01-09 04:45:25.853715+00	t	29	366
367	2019-01-09 04:45:25.886506+00	2019-01-09 04:45:25.886521+00	t	29	367
368	2019-01-09 04:45:25.917146+00	2019-01-09 04:45:25.91716+00	t	29	368
369	2019-01-09 04:45:25.948842+00	2019-01-09 04:45:25.948856+00	t	29	369
370	2019-01-09 04:45:25.982747+00	2019-01-09 04:45:25.982761+00	t	29	370
371	2019-01-09 04:45:26.040074+00	2019-01-09 04:45:26.040093+00	t	29	371
372	2019-01-09 04:45:26.07171+00	2019-01-09 04:45:26.071726+00	t	30	372
373	2019-01-09 04:45:26.113055+00	2019-01-09 04:45:26.11307+00	t	30	373
374	2019-01-09 04:45:26.145041+00	2019-01-09 04:45:26.145055+00	t	30	374
375	2019-01-09 04:45:26.175305+00	2019-01-09 04:45:26.175319+00	t	30	375
376	2019-01-09 04:45:26.205101+00	2019-01-09 04:45:26.205118+00	t	30	376
377	2019-01-09 04:45:26.235904+00	2019-01-09 04:45:26.235919+00	t	30	377
378	2019-01-09 04:45:26.26654+00	2019-01-09 04:45:26.266554+00	t	30	378
379	2019-01-09 04:45:26.298735+00	2019-01-09 04:45:26.29875+00	t	30	379
380	2019-01-09 04:45:26.330163+00	2019-01-09 04:45:26.330178+00	t	30	380
381	2019-01-09 09:44:04.339636+00	2019-01-09 09:44:04.33965+00	t	13	381
382	2019-01-09 09:44:04.376198+00	2019-01-09 09:44:04.376213+00	t	13	382
383	2019-01-09 09:44:04.408625+00	2019-01-09 09:44:04.408639+00	t	13	383
384	2019-01-09 09:44:04.442028+00	2019-01-09 09:44:04.442042+00	t	13	384
385	2019-01-09 09:44:04.476667+00	2019-01-09 09:44:04.47669+00	t	13	385
386	2019-01-09 09:44:04.510994+00	2019-01-09 09:44:04.511015+00	t	10	386
387	2019-01-09 09:44:04.544515+00	2019-01-09 09:44:04.544531+00	t	10	387
388	2019-01-09 09:44:04.57656+00	2019-01-09 09:44:04.576577+00	t	10	388
\.


--
-- Data for Name: products_productcategoryhistory; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productcategoryhistory (id, created_at, modified_at, status, category_id, product_id) FROM stdin;
\.


--
-- Data for Name: products_productcsv; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productcsv (id, file, uploaded_at) FROM stdin;
\.


--
-- Data for Name: products_producthistory; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_producthistory (id, product_name, product_short_description, product_long_description, product_sku, product_ean_code, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: products_productimage; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productimage (id, image_name, image_alt_text, image, created_at, modified_at, status, product_id) FROM stdin;
1	bhujia	\N	product_image/1.jpg	2019-01-09 07:45:38.757939+00	2019-01-09 07:45:38.757977+00	t	342
2	aqws	\N	product_image/-haldiram-bhujia-400gm.jpg	2019-01-09 07:47:52.67671+00	2019-01-09 07:47:52.676742+00	t	343
\.


--
-- Data for Name: products_productoption; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productoption (id, created_at, modified_at, color_id, flavor_id, fragrance_id, package_size_id, product_id, size_id, weight_id) FROM stdin;
28	2019-01-08 08:24:54.463302+00	2019-01-08 08:24:54.463316+00	\N	\N	\N	\N	28	\N	\N
29	2019-01-08 08:24:54.495022+00	2019-01-08 08:24:54.495039+00	\N	\N	\N	\N	29	\N	\N
30	2019-01-08 08:24:54.526614+00	2019-01-08 08:24:54.526629+00	\N	\N	\N	\N	30	\N	\N
31	2019-01-08 08:24:54.558114+00	2019-01-08 08:24:54.558128+00	\N	\N	\N	\N	31	\N	\N
32	2019-01-08 08:24:54.589668+00	2019-01-08 08:24:54.589682+00	\N	\N	\N	\N	32	\N	\N
33	2019-01-08 08:24:54.620619+00	2019-01-08 08:24:54.620637+00	\N	\N	\N	\N	33	\N	\N
34	2019-01-08 08:24:54.651729+00	2019-01-08 08:24:54.651744+00	\N	\N	\N	\N	34	\N	\N
35	2019-01-08 08:24:54.683635+00	2019-01-08 08:24:54.68365+00	\N	\N	\N	\N	35	\N	\N
36	2019-01-08 08:24:54.714731+00	2019-01-08 08:24:54.714745+00	\N	\N	\N	\N	36	\N	\N
37	2019-01-08 08:24:54.744812+00	2019-01-08 08:24:54.744826+00	\N	\N	\N	\N	37	\N	\N
38	2019-01-08 08:24:54.775286+00	2019-01-08 08:24:54.775301+00	\N	\N	\N	\N	38	\N	\N
39	2019-01-08 08:24:54.805708+00	2019-01-08 08:24:54.805723+00	\N	\N	\N	\N	39	\N	\N
40	2019-01-08 08:24:54.856639+00	2019-01-08 08:24:54.856661+00	\N	\N	\N	\N	40	\N	\N
41	2019-01-08 14:12:04.053673+00	2019-01-08 14:12:04.053691+00	\N	\N	\N	\N	41	\N	\N
42	2019-01-08 14:12:04.092652+00	2019-01-08 14:12:04.092669+00	\N	\N	\N	\N	42	\N	\N
43	2019-01-08 14:12:04.12655+00	2019-01-08 14:12:04.126566+00	\N	\N	\N	\N	43	\N	\N
44	2019-01-08 14:12:04.1659+00	2019-01-08 14:12:04.165921+00	\N	\N	\N	\N	44	\N	\N
45	2019-01-08 14:12:04.199352+00	2019-01-08 14:12:04.199372+00	\N	\N	\N	\N	45	\N	\N
46	2019-01-08 14:12:04.238868+00	2019-01-08 14:12:04.238889+00	\N	\N	\N	\N	46	\N	\N
47	2019-01-08 14:12:04.272776+00	2019-01-08 14:12:04.272791+00	\N	\N	\N	\N	47	\N	\N
48	2019-01-08 14:12:04.310854+00	2019-01-08 14:12:04.310871+00	\N	\N	\N	\N	48	\N	\N
49	2019-01-08 14:12:04.345264+00	2019-01-08 14:12:04.345281+00	\N	\N	\N	\N	49	\N	\N
50	2019-01-08 14:12:04.379027+00	2019-01-08 14:12:04.379042+00	\N	\N	\N	\N	50	\N	\N
51	2019-01-08 14:12:04.41222+00	2019-01-08 14:12:04.412239+00	\N	\N	\N	\N	51	\N	\N
52	2019-01-08 14:12:04.448841+00	2019-01-08 14:12:04.448855+00	\N	\N	\N	\N	52	\N	\N
53	2019-01-08 14:12:04.481971+00	2019-01-08 14:12:04.481988+00	\N	\N	\N	\N	53	\N	\N
54	2019-01-08 14:12:04.51684+00	2019-01-08 14:12:04.516858+00	\N	\N	\N	\N	54	\N	\N
55	2019-01-08 14:12:04.551373+00	2019-01-08 14:12:04.55139+00	\N	\N	\N	\N	55	\N	\N
56	2019-01-08 14:12:04.583209+00	2019-01-08 14:12:04.583226+00	\N	\N	\N	\N	56	\N	\N
57	2019-01-08 14:12:04.615426+00	2019-01-08 14:12:04.615442+00	\N	\N	\N	\N	57	\N	\N
58	2019-01-08 14:12:04.648006+00	2019-01-08 14:12:04.648024+00	\N	\N	\N	\N	58	\N	\N
59	2019-01-08 14:12:04.681949+00	2019-01-08 14:12:04.681968+00	\N	\N	\N	\N	59	\N	\N
60	2019-01-08 14:12:04.715755+00	2019-01-08 14:12:04.71577+00	\N	\N	\N	\N	60	\N	\N
61	2019-01-08 14:12:04.748697+00	2019-01-08 14:12:04.748712+00	\N	\N	\N	\N	61	\N	\N
62	2019-01-08 14:12:04.781972+00	2019-01-08 14:12:04.781992+00	\N	\N	\N	\N	62	\N	\N
63	2019-01-08 14:12:04.815964+00	2019-01-08 14:12:04.815986+00	\N	\N	\N	\N	63	\N	\N
64	2019-01-08 14:12:04.854727+00	2019-01-08 14:12:04.854748+00	\N	\N	\N	\N	64	\N	\N
65	2019-01-08 14:12:04.891914+00	2019-01-08 14:12:04.891939+00	\N	\N	\N	\N	65	\N	\N
66	2019-01-08 14:12:04.927341+00	2019-01-08 14:12:04.927358+00	\N	\N	\N	\N	66	\N	\N
67	2019-01-08 14:12:04.959858+00	2019-01-08 14:12:04.959876+00	\N	\N	\N	\N	67	\N	\N
68	2019-01-08 14:12:04.992878+00	2019-01-08 14:12:04.992894+00	\N	\N	\N	\N	68	\N	\N
69	2019-01-08 14:12:05.057838+00	2019-01-08 14:12:05.057853+00	\N	\N	\N	\N	69	\N	\N
70	2019-01-08 14:12:05.093382+00	2019-01-08 14:12:05.093397+00	\N	\N	\N	\N	70	\N	\N
71	2019-01-08 14:12:05.125466+00	2019-01-08 14:12:05.125481+00	\N	\N	\N	\N	71	\N	\N
72	2019-01-08 14:12:05.158768+00	2019-01-08 14:12:05.158782+00	\N	\N	\N	\N	72	\N	\N
73	2019-01-08 14:12:05.191417+00	2019-01-08 14:12:05.191432+00	\N	\N	\N	\N	73	\N	\N
74	2019-01-08 14:12:05.225258+00	2019-01-08 14:12:05.225274+00	\N	\N	\N	\N	74	\N	\N
75	2019-01-08 14:12:05.259226+00	2019-01-08 14:12:05.259245+00	\N	\N	\N	\N	75	\N	\N
76	2019-01-08 14:12:05.292679+00	2019-01-08 14:12:05.292694+00	\N	\N	\N	\N	76	\N	\N
77	2019-01-08 14:12:05.326934+00	2019-01-08 14:12:05.326953+00	\N	\N	\N	\N	77	\N	\N
78	2019-01-08 14:12:05.360049+00	2019-01-08 14:12:05.360065+00	\N	\N	\N	\N	78	\N	\N
79	2019-01-08 14:12:05.400368+00	2019-01-08 14:12:05.400382+00	\N	\N	\N	\N	79	\N	\N
80	2019-01-08 14:12:05.436837+00	2019-01-08 14:12:05.436857+00	\N	\N	\N	\N	80	\N	\N
81	2019-01-08 14:12:05.469913+00	2019-01-08 14:12:05.469931+00	\N	\N	\N	\N	81	\N	\N
82	2019-01-08 14:12:05.50167+00	2019-01-08 14:12:05.501686+00	\N	\N	\N	\N	82	\N	\N
83	2019-01-08 14:12:05.533731+00	2019-01-08 14:12:05.533752+00	\N	\N	\N	\N	83	\N	\N
84	2019-01-08 14:12:05.566343+00	2019-01-08 14:12:05.56636+00	\N	\N	\N	\N	84	\N	\N
85	2019-01-08 14:12:05.599542+00	2019-01-08 14:12:05.599562+00	\N	\N	\N	\N	85	\N	\N
86	2019-01-08 14:12:05.635947+00	2019-01-08 14:12:05.635966+00	\N	\N	\N	\N	86	\N	\N
87	2019-01-08 14:12:05.667622+00	2019-01-08 14:12:05.667637+00	\N	\N	\N	\N	87	\N	\N
88	2019-01-08 14:12:05.702975+00	2019-01-08 14:12:05.702992+00	\N	\N	\N	\N	88	\N	\N
89	2019-01-08 14:12:05.737462+00	2019-01-08 14:12:05.73748+00	\N	\N	\N	\N	89	\N	\N
90	2019-01-08 14:12:05.774967+00	2019-01-08 14:12:05.774988+00	\N	\N	\N	\N	90	\N	\N
91	2019-01-08 14:12:05.812318+00	2019-01-08 14:12:05.812334+00	\N	\N	\N	\N	91	\N	\N
92	2019-01-08 14:12:05.846693+00	2019-01-08 14:12:05.846709+00	\N	\N	\N	\N	92	\N	\N
93	2019-01-08 14:12:05.878972+00	2019-01-08 14:12:05.878992+00	\N	\N	\N	\N	93	\N	\N
94	2019-01-08 14:12:05.911437+00	2019-01-08 14:12:05.911452+00	\N	\N	\N	\N	94	\N	\N
95	2019-01-08 14:12:05.94319+00	2019-01-08 14:12:05.943205+00	\N	\N	\N	\N	95	\N	\N
96	2019-01-08 14:12:05.976698+00	2019-01-08 14:12:05.976712+00	\N	\N	\N	\N	96	\N	\N
97	2019-01-08 14:12:06.015785+00	2019-01-08 14:12:06.015808+00	\N	\N	\N	\N	97	\N	\N
98	2019-01-08 14:12:06.050012+00	2019-01-08 14:12:06.050028+00	\N	\N	\N	\N	98	\N	\N
99	2019-01-08 14:12:06.083508+00	2019-01-08 14:12:06.083526+00	\N	\N	\N	\N	99	\N	\N
100	2019-01-08 14:12:06.117608+00	2019-01-08 14:12:06.117625+00	\N	\N	\N	\N	100	\N	\N
101	2019-01-08 14:12:06.150694+00	2019-01-08 14:12:06.150713+00	\N	\N	\N	\N	101	\N	\N
102	2019-01-08 14:12:06.182816+00	2019-01-08 14:12:06.182831+00	\N	\N	\N	\N	102	\N	\N
103	2019-01-08 14:12:06.214998+00	2019-01-08 14:12:06.215013+00	\N	\N	\N	\N	103	\N	\N
104	2019-01-08 14:12:06.247187+00	2019-01-08 14:12:06.247205+00	\N	\N	\N	\N	104	\N	\N
105	2019-01-08 14:12:06.279441+00	2019-01-08 14:12:06.279456+00	\N	\N	\N	\N	105	\N	\N
106	2019-01-08 14:12:06.312176+00	2019-01-08 14:12:06.312191+00	\N	\N	\N	\N	106	\N	\N
107	2019-01-08 14:12:06.346182+00	2019-01-08 14:12:06.3462+00	\N	\N	\N	\N	107	\N	\N
108	2019-01-08 14:12:06.379569+00	2019-01-08 14:12:06.379592+00	\N	\N	\N	\N	108	\N	\N
109	2019-01-08 14:12:06.412582+00	2019-01-08 14:12:06.412601+00	\N	\N	\N	\N	109	\N	\N
110	2019-01-08 14:12:06.44533+00	2019-01-08 14:12:06.445346+00	\N	\N	\N	\N	110	\N	\N
111	2019-01-08 14:12:06.477974+00	2019-01-08 14:12:06.477993+00	\N	\N	\N	\N	111	\N	\N
112	2019-01-08 14:12:06.511581+00	2019-01-08 14:12:06.511595+00	\N	\N	\N	\N	112	\N	\N
113	2019-01-08 14:12:06.543554+00	2019-01-08 14:12:06.543573+00	\N	\N	\N	\N	113	\N	\N
114	2019-01-08 14:12:06.575515+00	2019-01-08 14:12:06.575531+00	\N	\N	\N	\N	114	\N	\N
115	2019-01-08 14:12:06.606695+00	2019-01-08 14:12:06.606713+00	\N	\N	\N	\N	115	\N	\N
116	2019-01-08 14:12:06.637585+00	2019-01-08 14:12:06.637601+00	\N	\N	\N	\N	116	\N	\N
117	2019-01-08 14:12:06.669253+00	2019-01-08 14:12:06.669272+00	\N	\N	\N	\N	117	\N	\N
118	2019-01-08 14:12:06.705786+00	2019-01-08 14:12:06.705805+00	\N	\N	\N	\N	118	\N	\N
119	2019-01-08 14:12:06.744426+00	2019-01-08 14:12:06.74445+00	\N	\N	\N	\N	119	\N	\N
120	2019-01-08 14:12:06.776437+00	2019-01-08 14:12:06.776454+00	\N	\N	\N	\N	120	\N	\N
121	2019-01-08 14:12:06.807523+00	2019-01-08 14:12:06.807537+00	\N	\N	\N	\N	121	\N	\N
122	2019-01-08 14:12:06.839735+00	2019-01-08 14:12:06.83975+00	\N	\N	\N	\N	122	\N	\N
123	2019-01-08 14:12:06.872425+00	2019-01-08 14:12:06.872439+00	\N	\N	\N	\N	123	\N	\N
124	2019-01-08 14:12:06.905009+00	2019-01-08 14:12:06.905029+00	\N	\N	\N	\N	124	\N	\N
125	2019-01-08 14:12:06.936571+00	2019-01-08 14:12:06.936585+00	\N	\N	\N	\N	125	\N	\N
126	2019-01-08 14:12:06.968417+00	2019-01-08 14:12:06.968432+00	\N	\N	\N	\N	126	\N	\N
127	2019-01-08 14:12:07.000316+00	2019-01-08 14:12:07.00033+00	\N	\N	\N	\N	127	\N	\N
128	2019-01-08 14:12:07.032413+00	2019-01-08 14:12:07.032429+00	\N	\N	\N	\N	128	\N	\N
129	2019-01-08 14:12:07.064051+00	2019-01-08 14:12:07.064067+00	\N	\N	\N	\N	129	\N	\N
130	2019-01-08 14:12:07.095854+00	2019-01-08 14:12:07.09587+00	\N	\N	\N	\N	130	\N	\N
131	2019-01-08 14:12:07.127896+00	2019-01-08 14:12:07.127912+00	\N	\N	\N	\N	131	\N	\N
132	2019-01-08 14:12:07.159781+00	2019-01-08 14:12:07.159796+00	\N	\N	\N	\N	132	\N	\N
133	2019-01-08 14:12:07.191523+00	2019-01-08 14:12:07.191539+00	\N	\N	\N	\N	133	\N	\N
134	2019-01-08 14:12:07.225044+00	2019-01-08 14:12:07.225063+00	\N	\N	\N	\N	134	\N	\N
135	2019-01-08 14:12:07.25728+00	2019-01-08 14:12:07.257304+00	\N	\N	\N	\N	135	\N	\N
136	2019-01-08 14:12:07.288999+00	2019-01-08 14:12:07.289014+00	\N	\N	\N	\N	136	\N	\N
137	2019-01-08 14:12:07.320765+00	2019-01-08 14:12:07.320784+00	\N	\N	\N	\N	137	\N	\N
138	2019-01-08 14:12:07.35334+00	2019-01-08 14:12:07.353355+00	\N	\N	\N	\N	138	\N	\N
139	2019-01-08 14:12:07.385779+00	2019-01-08 14:12:07.385804+00	\N	\N	\N	\N	139	\N	\N
140	2019-01-08 14:12:07.417205+00	2019-01-08 14:12:07.417224+00	\N	\N	\N	\N	140	\N	\N
141	2019-01-08 14:12:07.450567+00	2019-01-08 14:12:07.450581+00	\N	\N	\N	\N	141	\N	\N
142	2019-01-08 14:12:07.481601+00	2019-01-08 14:12:07.481618+00	\N	\N	\N	\N	142	\N	\N
143	2019-01-08 14:12:07.513772+00	2019-01-08 14:12:07.513792+00	\N	\N	\N	\N	143	\N	\N
144	2019-01-08 14:12:07.546825+00	2019-01-08 14:12:07.546842+00	\N	\N	\N	\N	144	\N	\N
145	2019-01-08 14:12:07.578849+00	2019-01-08 14:12:07.578868+00	\N	\N	\N	\N	145	\N	\N
146	2019-01-08 14:12:07.611481+00	2019-01-08 14:12:07.611502+00	\N	\N	\N	\N	146	\N	\N
147	2019-01-08 14:12:07.643886+00	2019-01-08 14:12:07.643906+00	\N	\N	\N	\N	147	\N	\N
148	2019-01-08 14:12:07.676153+00	2019-01-08 14:12:07.676172+00	\N	\N	\N	\N	148	\N	\N
149	2019-01-08 14:12:07.708473+00	2019-01-08 14:12:07.708489+00	\N	\N	\N	\N	149	\N	\N
150	2019-01-08 14:12:07.739771+00	2019-01-08 14:12:07.739785+00	\N	\N	\N	\N	150	\N	\N
151	2019-01-08 14:12:07.771531+00	2019-01-08 14:12:07.77155+00	\N	\N	\N	\N	151	\N	\N
152	2019-01-08 14:12:07.804725+00	2019-01-08 14:12:07.804743+00	\N	\N	\N	\N	152	\N	\N
153	2019-01-08 14:12:07.836343+00	2019-01-08 14:12:07.836362+00	\N	\N	\N	\N	153	\N	\N
154	2019-01-08 14:12:07.869362+00	2019-01-08 14:12:07.869383+00	\N	\N	\N	\N	154	\N	\N
155	2019-01-08 14:12:07.901012+00	2019-01-08 14:12:07.901029+00	\N	\N	\N	\N	155	\N	\N
156	2019-01-08 14:12:07.933216+00	2019-01-08 14:12:07.933235+00	\N	\N	\N	\N	156	\N	\N
157	2019-01-08 14:12:07.964752+00	2019-01-08 14:12:07.964767+00	\N	\N	\N	\N	157	\N	\N
158	2019-01-08 14:12:07.996097+00	2019-01-08 14:12:07.996113+00	\N	\N	\N	\N	158	\N	\N
159	2019-01-08 14:12:08.031922+00	2019-01-08 14:12:08.03194+00	\N	\N	\N	\N	159	\N	\N
160	2019-01-08 14:12:08.064051+00	2019-01-08 14:12:08.064069+00	\N	\N	\N	\N	160	\N	\N
161	2019-01-08 14:12:08.096955+00	2019-01-08 14:12:08.096979+00	\N	\N	\N	\N	161	\N	\N
162	2019-01-08 14:12:08.131018+00	2019-01-08 14:12:08.131035+00	\N	\N	\N	\N	162	\N	\N
163	2019-01-08 14:12:08.163798+00	2019-01-08 14:12:08.163816+00	\N	\N	\N	\N	163	\N	\N
164	2019-01-08 14:12:08.196073+00	2019-01-08 14:12:08.196096+00	\N	\N	\N	\N	164	\N	\N
165	2019-01-08 14:12:08.228901+00	2019-01-08 14:12:08.228918+00	\N	\N	\N	\N	165	\N	\N
166	2019-01-08 14:12:08.262085+00	2019-01-08 14:12:08.262101+00	\N	\N	\N	\N	166	\N	\N
167	2019-01-08 14:12:08.294523+00	2019-01-08 14:12:08.294543+00	\N	\N	\N	\N	167	\N	\N
168	2019-01-08 14:12:08.326973+00	2019-01-08 14:12:08.326992+00	\N	\N	\N	\N	168	\N	\N
169	2019-01-08 14:12:08.360921+00	2019-01-08 14:12:08.360954+00	\N	\N	\N	\N	169	\N	\N
170	2019-01-08 14:12:08.393385+00	2019-01-08 14:12:08.393405+00	\N	\N	\N	\N	170	\N	\N
171	2019-01-08 14:12:08.425157+00	2019-01-08 14:12:08.425175+00	\N	\N	\N	\N	171	\N	\N
172	2019-01-08 14:12:08.457068+00	2019-01-08 14:12:08.45709+00	\N	\N	\N	\N	172	\N	\N
173	2019-01-08 14:12:08.496321+00	2019-01-08 14:12:08.496339+00	\N	\N	\N	\N	173	\N	\N
174	2019-01-08 14:12:08.529333+00	2019-01-08 14:12:08.529362+00	\N	\N	\N	\N	174	\N	\N
175	2019-01-08 14:12:08.562349+00	2019-01-08 14:12:08.56237+00	\N	\N	\N	\N	175	\N	\N
176	2019-01-08 14:12:08.595879+00	2019-01-08 14:12:08.595899+00	\N	\N	\N	\N	176	\N	\N
177	2019-01-08 14:12:08.630634+00	2019-01-08 14:12:08.63066+00	\N	\N	\N	\N	177	\N	\N
178	2019-01-08 14:12:08.664118+00	2019-01-08 14:12:08.664133+00	\N	\N	\N	\N	178	\N	\N
179	2019-01-08 14:12:08.697283+00	2019-01-08 14:12:08.697299+00	\N	\N	\N	\N	179	\N	\N
180	2019-01-08 14:12:08.72948+00	2019-01-08 14:12:08.7295+00	\N	\N	\N	\N	180	\N	\N
181	2019-01-08 14:12:08.761379+00	2019-01-08 14:12:08.761396+00	\N	\N	\N	\N	181	\N	\N
182	2019-01-08 14:12:08.792964+00	2019-01-08 14:12:08.792982+00	\N	\N	\N	\N	182	\N	\N
183	2019-01-08 14:12:08.823771+00	2019-01-08 14:12:08.823797+00	\N	\N	\N	\N	183	\N	\N
184	2019-01-08 14:12:08.858334+00	2019-01-08 14:12:08.85835+00	\N	\N	\N	\N	184	\N	\N
185	2019-01-08 14:12:08.890263+00	2019-01-08 14:12:08.890281+00	\N	\N	\N	\N	185	\N	\N
186	2019-01-08 14:12:08.922054+00	2019-01-08 14:12:08.92207+00	\N	\N	\N	\N	186	\N	\N
187	2019-01-08 14:12:08.954908+00	2019-01-08 14:12:08.954923+00	\N	\N	\N	\N	187	\N	\N
188	2019-01-08 14:12:08.986813+00	2019-01-08 14:12:08.986832+00	\N	\N	\N	\N	188	\N	\N
189	2019-01-08 14:12:09.021783+00	2019-01-08 14:12:09.021802+00	\N	\N	\N	\N	189	\N	\N
190	2019-01-08 14:12:09.05451+00	2019-01-08 14:12:09.054528+00	\N	\N	\N	\N	190	\N	\N
191	2019-01-08 14:12:09.086733+00	2019-01-08 14:12:09.086753+00	\N	\N	\N	\N	191	\N	\N
192	2019-01-08 14:12:09.120024+00	2019-01-08 14:12:09.120048+00	\N	\N	\N	\N	192	\N	\N
193	2019-01-08 14:12:09.153075+00	2019-01-08 14:12:09.153092+00	\N	\N	\N	\N	193	\N	\N
194	2019-01-08 14:12:09.18551+00	2019-01-08 14:12:09.185529+00	\N	\N	\N	\N	194	\N	\N
195	2019-01-08 14:12:09.217172+00	2019-01-08 14:12:09.217187+00	\N	\N	\N	\N	195	\N	\N
196	2019-01-08 14:12:09.248187+00	2019-01-08 14:12:09.248205+00	\N	\N	\N	\N	196	\N	\N
197	2019-01-08 14:12:09.280568+00	2019-01-08 14:12:09.280584+00	\N	\N	\N	\N	197	\N	\N
198	2019-01-08 14:12:09.312108+00	2019-01-08 14:12:09.312128+00	\N	\N	\N	\N	198	\N	\N
199	2019-01-08 14:12:09.343882+00	2019-01-08 14:12:09.3439+00	\N	\N	\N	\N	199	\N	\N
200	2019-01-08 14:12:09.375794+00	2019-01-08 14:12:09.375812+00	\N	\N	\N	\N	200	\N	\N
201	2019-01-08 14:12:09.409753+00	2019-01-08 14:12:09.409772+00	\N	\N	\N	\N	201	\N	\N
202	2019-01-08 14:12:09.441619+00	2019-01-08 14:12:09.441634+00	\N	\N	\N	\N	202	\N	\N
203	2019-01-08 14:12:09.472999+00	2019-01-08 14:12:09.473015+00	\N	\N	\N	\N	203	\N	\N
204	2019-01-08 14:12:09.504324+00	2019-01-08 14:12:09.504341+00	\N	\N	\N	\N	204	\N	\N
205	2019-01-08 14:12:09.53498+00	2019-01-08 14:12:09.534999+00	\N	\N	\N	\N	205	\N	\N
206	2019-01-08 14:12:09.568917+00	2019-01-08 14:12:09.568936+00	\N	\N	\N	\N	206	\N	\N
207	2019-01-08 14:12:09.600644+00	2019-01-08 14:12:09.60066+00	\N	\N	\N	\N	207	\N	\N
208	2019-01-08 14:12:09.633564+00	2019-01-08 14:12:09.633586+00	\N	\N	\N	\N	208	\N	\N
209	2019-01-08 14:12:09.666194+00	2019-01-08 14:12:09.666214+00	\N	\N	\N	\N	209	\N	\N
210	2019-01-08 14:12:09.698166+00	2019-01-08 14:12:09.698192+00	\N	\N	\N	\N	210	\N	\N
211	2019-01-08 14:12:09.730901+00	2019-01-08 14:12:09.730922+00	\N	\N	\N	\N	211	\N	\N
212	2019-01-08 14:12:09.763008+00	2019-01-08 14:12:09.763024+00	\N	\N	\N	\N	212	\N	\N
213	2019-01-08 14:12:09.794335+00	2019-01-08 14:12:09.794352+00	\N	\N	\N	\N	213	\N	\N
214	2019-01-08 14:12:09.826924+00	2019-01-08 14:12:09.826943+00	\N	\N	\N	\N	214	\N	\N
215	2019-01-08 14:12:09.876461+00	2019-01-08 14:12:09.876481+00	\N	\N	\N	\N	215	\N	\N
216	2019-01-08 14:12:09.909071+00	2019-01-08 14:12:09.9091+00	\N	\N	\N	\N	216	\N	\N
217	2019-01-08 14:12:09.942462+00	2019-01-08 14:12:09.942488+00	\N	\N	\N	\N	217	\N	\N
218	2019-01-08 14:12:09.974324+00	2019-01-08 14:12:09.97434+00	\N	\N	\N	\N	218	\N	\N
219	2019-01-08 14:12:10.072613+00	2019-01-08 14:12:10.072631+00	\N	\N	\N	\N	219	\N	\N
220	2019-01-08 14:12:10.104495+00	2019-01-08 14:12:10.104513+00	\N	\N	\N	\N	220	\N	\N
221	2019-01-08 14:12:10.137025+00	2019-01-08 14:12:10.137043+00	\N	\N	\N	\N	221	\N	\N
222	2019-01-08 14:12:10.172091+00	2019-01-08 14:12:10.17211+00	\N	\N	\N	\N	222	\N	\N
223	2019-01-08 14:12:10.208341+00	2019-01-08 14:12:10.208365+00	\N	\N	\N	\N	223	\N	\N
224	2019-01-08 14:12:10.241267+00	2019-01-08 14:12:10.241288+00	\N	\N	\N	\N	224	\N	\N
225	2019-01-08 14:12:10.274113+00	2019-01-08 14:12:10.274131+00	\N	\N	\N	\N	225	\N	\N
226	2019-01-08 14:12:10.306308+00	2019-01-08 14:12:10.306323+00	\N	\N	\N	\N	226	\N	\N
227	2019-01-08 14:12:10.3419+00	2019-01-08 14:12:10.341926+00	\N	\N	\N	\N	227	\N	\N
228	2019-01-08 14:12:10.379752+00	2019-01-08 14:12:10.379775+00	\N	\N	\N	\N	228	\N	\N
229	2019-01-08 14:12:10.417419+00	2019-01-08 14:12:10.417441+00	\N	\N	\N	\N	229	\N	\N
230	2019-01-08 14:12:10.453902+00	2019-01-08 14:12:10.453922+00	\N	\N	\N	\N	230	\N	\N
231	2019-01-08 14:12:10.487791+00	2019-01-08 14:12:10.487809+00	\N	\N	\N	\N	231	\N	\N
232	2019-01-08 14:12:10.526016+00	2019-01-08 14:12:10.526036+00	\N	\N	\N	\N	232	\N	\N
233	2019-01-08 14:12:10.561611+00	2019-01-08 14:12:10.561627+00	\N	\N	\N	\N	233	\N	\N
234	2019-01-08 14:12:10.596169+00	2019-01-08 14:12:10.596186+00	\N	\N	\N	\N	234	\N	\N
235	2019-01-08 14:12:10.630607+00	2019-01-08 14:12:10.630625+00	\N	\N	\N	\N	235	\N	\N
236	2019-01-08 14:12:10.665614+00	2019-01-08 14:12:10.665634+00	\N	\N	\N	\N	236	\N	\N
237	2019-01-08 14:12:10.700063+00	2019-01-08 14:12:10.700082+00	\N	\N	\N	\N	237	\N	\N
238	2019-01-08 14:12:10.732959+00	2019-01-08 14:12:10.732976+00	\N	\N	\N	\N	238	\N	\N
239	2019-01-08 14:12:10.765534+00	2019-01-08 14:12:10.765554+00	\N	\N	\N	\N	239	\N	\N
240	2019-01-08 14:12:10.798081+00	2019-01-08 14:12:10.798098+00	\N	\N	\N	\N	240	\N	\N
241	2019-01-08 14:12:10.833785+00	2019-01-08 14:12:10.833811+00	\N	\N	\N	\N	241	\N	\N
242	2019-01-08 14:12:10.869083+00	2019-01-08 14:12:10.8691+00	\N	\N	\N	\N	242	\N	\N
243	2019-01-08 14:12:10.903217+00	2019-01-08 14:12:10.903233+00	\N	\N	\N	\N	243	\N	\N
244	2019-01-08 14:12:10.936081+00	2019-01-08 14:12:10.936095+00	\N	\N	\N	\N	244	\N	\N
245	2019-01-08 14:12:10.970624+00	2019-01-08 14:12:10.97064+00	\N	\N	\N	\N	245	\N	\N
246	2019-01-08 14:12:11.006765+00	2019-01-08 14:12:11.006783+00	\N	\N	\N	\N	246	\N	\N
247	2019-01-08 14:12:11.04023+00	2019-01-08 14:12:11.040246+00	\N	\N	\N	\N	247	\N	\N
248	2019-01-08 14:12:11.07621+00	2019-01-08 14:12:11.076231+00	\N	\N	\N	\N	248	\N	\N
249	2019-01-08 14:12:11.109689+00	2019-01-08 14:12:11.109711+00	\N	\N	\N	\N	249	\N	\N
250	2019-01-08 14:12:11.142173+00	2019-01-08 14:12:11.142191+00	\N	\N	\N	\N	250	\N	\N
251	2019-01-08 14:12:11.174926+00	2019-01-08 14:12:11.174943+00	\N	\N	\N	\N	251	\N	\N
252	2019-01-08 14:12:11.207302+00	2019-01-08 14:12:11.207319+00	\N	\N	\N	\N	252	\N	\N
253	2019-01-08 14:12:11.240403+00	2019-01-08 14:12:11.240418+00	\N	\N	\N	\N	253	\N	\N
254	2019-01-08 14:12:11.276763+00	2019-01-08 14:12:11.27678+00	\N	\N	\N	\N	254	\N	\N
255	2019-01-08 14:12:11.314546+00	2019-01-08 14:12:11.314565+00	\N	\N	\N	\N	255	\N	\N
256	2019-01-08 14:12:11.34767+00	2019-01-08 14:12:11.347689+00	\N	\N	\N	\N	256	\N	\N
257	2019-01-08 14:12:11.380611+00	2019-01-08 14:12:11.380629+00	\N	\N	\N	\N	257	\N	\N
258	2019-01-08 14:12:11.414263+00	2019-01-08 14:12:11.414282+00	\N	\N	\N	\N	258	\N	\N
259	2019-01-08 14:12:11.446039+00	2019-01-08 14:12:11.446055+00	\N	\N	\N	\N	259	\N	\N
260	2019-01-08 14:12:11.478861+00	2019-01-08 14:12:11.478882+00	\N	\N	\N	\N	260	\N	\N
261	2019-01-08 14:12:11.512681+00	2019-01-08 14:12:11.512696+00	\N	\N	\N	\N	261	\N	\N
262	2019-01-08 14:12:11.545138+00	2019-01-08 14:12:11.545154+00	\N	\N	\N	\N	262	\N	\N
263	2019-01-08 14:12:11.577155+00	2019-01-08 14:12:11.577172+00	\N	\N	\N	\N	263	\N	\N
264	2019-01-08 14:12:11.608918+00	2019-01-08 14:12:11.608937+00	\N	\N	\N	\N	264	\N	\N
265	2019-01-08 14:12:11.642432+00	2019-01-08 14:12:11.642454+00	\N	\N	\N	\N	265	\N	\N
266	2019-01-08 14:12:11.674436+00	2019-01-08 14:12:11.674453+00	\N	\N	\N	\N	266	\N	\N
267	2019-01-08 14:12:11.70632+00	2019-01-08 14:12:11.706337+00	\N	\N	\N	\N	267	\N	\N
268	2019-01-08 14:12:11.738455+00	2019-01-08 14:12:11.738471+00	\N	\N	\N	\N	268	\N	\N
269	2019-01-08 14:12:11.770423+00	2019-01-08 14:12:11.770442+00	\N	\N	\N	\N	269	\N	\N
270	2019-01-09 04:45:22.613008+00	2019-01-09 04:45:22.613021+00	\N	\N	\N	\N	270	\N	\N
271	2019-01-09 04:45:22.650997+00	2019-01-09 04:45:22.651012+00	\N	\N	\N	\N	271	\N	\N
272	2019-01-09 04:45:22.686795+00	2019-01-09 04:45:22.686812+00	\N	\N	\N	\N	272	\N	\N
273	2019-01-09 04:45:22.718007+00	2019-01-09 04:45:22.718021+00	\N	\N	\N	\N	273	\N	\N
274	2019-01-09 04:45:22.756452+00	2019-01-09 04:45:22.756472+00	\N	\N	\N	\N	274	\N	\N
275	2019-01-09 04:45:22.788685+00	2019-01-09 04:45:22.788699+00	\N	\N	\N	\N	275	\N	\N
276	2019-01-09 04:45:22.822303+00	2019-01-09 04:45:22.822318+00	\N	\N	\N	\N	276	\N	\N
277	2019-01-09 04:45:22.85707+00	2019-01-09 04:45:22.857084+00	\N	\N	\N	\N	277	\N	\N
278	2019-01-09 04:45:22.890034+00	2019-01-09 04:45:22.890047+00	\N	\N	\N	\N	278	\N	\N
279	2019-01-09 04:45:22.924916+00	2019-01-09 04:45:22.924929+00	\N	\N	\N	\N	279	\N	\N
280	2019-01-09 04:45:22.954679+00	2019-01-09 04:45:22.954694+00	\N	\N	\N	\N	280	\N	\N
281	2019-01-09 04:45:22.989738+00	2019-01-09 04:45:22.989752+00	\N	\N	\N	\N	281	\N	\N
282	2019-01-09 04:45:23.025001+00	2019-01-09 04:45:23.025015+00	\N	\N	\N	\N	282	\N	\N
283	2019-01-09 04:45:23.054995+00	2019-01-09 04:45:23.055009+00	\N	\N	\N	\N	283	\N	\N
284	2019-01-09 04:45:23.090354+00	2019-01-09 04:45:23.090368+00	\N	\N	\N	\N	284	\N	\N
285	2019-01-09 04:45:23.122897+00	2019-01-09 04:45:23.12291+00	\N	\N	\N	\N	285	\N	\N
286	2019-01-09 04:45:23.156535+00	2019-01-09 04:45:23.156551+00	\N	\N	\N	\N	286	\N	\N
287	2019-01-09 04:45:23.19275+00	2019-01-09 04:45:23.192763+00	\N	\N	\N	\N	287	\N	\N
288	2019-01-09 04:45:23.224527+00	2019-01-09 04:45:23.224544+00	\N	\N	\N	\N	288	\N	\N
289	2019-01-09 04:45:23.259825+00	2019-01-09 04:45:23.259841+00	\N	\N	\N	\N	289	\N	\N
290	2019-01-09 04:45:23.292014+00	2019-01-09 04:45:23.292027+00	\N	\N	\N	\N	290	\N	\N
291	2019-01-09 04:45:23.324205+00	2019-01-09 04:45:23.324219+00	\N	\N	\N	\N	291	\N	\N
292	2019-01-09 04:45:23.357136+00	2019-01-09 04:45:23.35715+00	\N	\N	\N	\N	292	\N	\N
293	2019-01-09 04:45:23.393347+00	2019-01-09 04:45:23.39336+00	\N	\N	\N	\N	293	\N	\N
294	2019-01-09 04:45:23.424365+00	2019-01-09 04:45:23.424379+00	\N	\N	\N	\N	294	\N	\N
295	2019-01-09 04:45:23.455594+00	2019-01-09 04:45:23.45561+00	\N	\N	\N	\N	295	\N	\N
296	2019-01-09 04:45:23.488554+00	2019-01-09 04:45:23.488568+00	\N	\N	\N	\N	296	\N	\N
297	2019-01-09 04:45:23.523264+00	2019-01-09 04:45:23.523278+00	\N	\N	\N	\N	297	\N	\N
298	2019-01-09 04:45:23.55489+00	2019-01-09 04:45:23.554904+00	\N	\N	\N	\N	298	\N	\N
299	2019-01-09 04:45:23.587519+00	2019-01-09 04:45:23.587535+00	\N	\N	\N	\N	299	\N	\N
300	2019-01-09 04:45:23.619297+00	2019-01-09 04:45:23.619311+00	\N	\N	\N	\N	300	\N	\N
301	2019-01-09 04:45:23.649923+00	2019-01-09 04:45:23.649936+00	\N	\N	\N	\N	301	\N	\N
302	2019-01-09 04:45:23.681519+00	2019-01-09 04:45:23.681536+00	\N	\N	\N	\N	302	\N	\N
303	2019-01-09 04:45:23.712399+00	2019-01-09 04:45:23.712415+00	\N	\N	\N	\N	303	\N	\N
304	2019-01-09 04:45:23.74263+00	2019-01-09 04:45:23.742644+00	\N	\N	\N	\N	304	\N	\N
305	2019-01-09 04:45:23.773819+00	2019-01-09 04:45:23.773833+00	\N	\N	\N	\N	305	\N	\N
306	2019-01-09 04:45:23.804919+00	2019-01-09 04:45:23.80494+00	\N	\N	\N	\N	306	\N	\N
307	2019-01-09 04:45:23.837735+00	2019-01-09 04:45:23.837749+00	\N	\N	\N	\N	307	\N	\N
308	2019-01-09 04:45:23.869497+00	2019-01-09 04:45:23.869512+00	\N	\N	\N	\N	308	\N	\N
309	2019-01-09 04:45:23.900367+00	2019-01-09 04:45:23.900384+00	\N	\N	\N	\N	309	\N	\N
310	2019-01-09 04:45:23.933294+00	2019-01-09 04:45:23.933312+00	\N	\N	\N	\N	310	\N	\N
311	2019-01-09 04:45:23.967752+00	2019-01-09 04:45:23.967765+00	\N	\N	\N	\N	311	\N	\N
312	2019-01-09 04:45:24.003154+00	2019-01-09 04:45:24.00318+00	\N	\N	\N	\N	312	\N	\N
313	2019-01-09 04:45:24.034484+00	2019-01-09 04:45:24.034499+00	\N	\N	\N	\N	313	\N	\N
314	2019-01-09 04:45:24.072106+00	2019-01-09 04:45:24.072121+00	\N	\N	\N	\N	314	\N	\N
315	2019-01-09 04:45:24.108037+00	2019-01-09 04:45:24.108055+00	\N	\N	\N	\N	315	\N	\N
316	2019-01-09 04:45:24.138638+00	2019-01-09 04:45:24.138652+00	\N	\N	\N	\N	316	\N	\N
317	2019-01-09 04:45:24.170998+00	2019-01-09 04:45:24.171012+00	\N	\N	\N	\N	317	\N	\N
318	2019-01-09 04:45:24.202392+00	2019-01-09 04:45:24.202412+00	\N	\N	\N	\N	318	\N	\N
319	2019-01-09 04:45:24.237439+00	2019-01-09 04:45:24.237455+00	\N	\N	\N	\N	319	\N	\N
320	2019-01-09 04:45:24.269198+00	2019-01-09 04:45:24.269212+00	\N	\N	\N	\N	320	\N	\N
321	2019-01-09 04:45:24.305454+00	2019-01-09 04:45:24.30547+00	\N	\N	\N	\N	321	\N	\N
322	2019-01-09 04:45:24.336873+00	2019-01-09 04:45:24.336888+00	\N	\N	\N	\N	322	\N	\N
323	2019-01-09 04:45:24.368687+00	2019-01-09 04:45:24.368705+00	\N	\N	\N	\N	323	\N	\N
324	2019-01-09 04:45:24.405655+00	2019-01-09 04:45:24.405672+00	\N	\N	\N	\N	324	\N	\N
325	2019-01-09 04:45:24.437402+00	2019-01-09 04:45:24.437419+00	\N	\N	\N	\N	325	\N	\N
326	2019-01-09 04:45:24.469463+00	2019-01-09 04:45:24.469479+00	\N	\N	\N	\N	326	\N	\N
327	2019-01-09 04:45:24.5026+00	2019-01-09 04:45:24.502615+00	\N	\N	\N	\N	327	\N	\N
328	2019-01-09 04:45:24.533524+00	2019-01-09 04:45:24.533546+00	\N	\N	\N	\N	328	\N	\N
329	2019-01-09 04:45:24.56537+00	2019-01-09 04:45:24.565385+00	\N	\N	\N	\N	329	\N	\N
330	2019-01-09 04:45:24.595656+00	2019-01-09 04:45:24.595669+00	\N	\N	\N	\N	330	\N	\N
331	2019-01-09 04:45:24.627074+00	2019-01-09 04:45:24.627089+00	\N	\N	\N	\N	331	\N	\N
332	2019-01-09 04:45:24.658017+00	2019-01-09 04:45:24.658031+00	\N	\N	\N	\N	332	\N	\N
333	2019-01-09 04:45:24.688676+00	2019-01-09 04:45:24.68869+00	\N	\N	\N	\N	333	\N	\N
334	2019-01-09 04:45:24.721814+00	2019-01-09 04:45:24.72183+00	\N	\N	\N	\N	334	\N	\N
335	2019-01-09 04:45:24.755795+00	2019-01-09 04:45:24.755809+00	\N	\N	\N	\N	335	\N	\N
336	2019-01-09 04:45:24.786777+00	2019-01-09 04:45:24.78679+00	\N	\N	\N	\N	336	\N	\N
337	2019-01-09 04:45:24.822716+00	2019-01-09 04:45:24.822735+00	\N	\N	\N	\N	337	\N	\N
338	2019-01-09 04:45:24.869394+00	2019-01-09 04:45:24.869408+00	\N	\N	\N	\N	338	\N	\N
339	2019-01-09 04:45:24.900407+00	2019-01-09 04:45:24.900422+00	\N	\N	\N	\N	339	\N	\N
340	2019-01-09 04:45:24.94135+00	2019-01-09 04:45:24.941372+00	\N	\N	\N	\N	340	\N	\N
341	2019-01-09 04:45:24.973696+00	2019-01-09 04:45:24.973711+00	\N	\N	\N	\N	341	\N	\N
342	2019-01-09 04:45:25.045709+00	2019-01-09 04:45:25.045738+00	\N	\N	\N	\N	342	\N	\N
343	2019-01-09 04:45:25.078659+00	2019-01-09 04:45:25.078684+00	\N	\N	\N	\N	343	\N	\N
344	2019-01-09 04:45:25.117773+00	2019-01-09 04:45:25.117795+00	\N	\N	\N	\N	344	\N	\N
345	2019-01-09 04:45:25.151128+00	2019-01-09 04:45:25.151158+00	\N	\N	\N	\N	345	\N	\N
346	2019-01-09 04:45:25.187703+00	2019-01-09 04:45:25.187722+00	\N	\N	\N	\N	346	\N	\N
347	2019-01-09 04:45:25.220422+00	2019-01-09 04:45:25.220438+00	\N	\N	\N	\N	347	\N	\N
348	2019-01-09 04:45:25.251557+00	2019-01-09 04:45:25.251571+00	\N	\N	\N	\N	348	\N	\N
349	2019-01-09 04:45:25.286328+00	2019-01-09 04:45:25.286342+00	\N	\N	\N	\N	349	\N	\N
350	2019-01-09 04:45:25.318357+00	2019-01-09 04:45:25.318371+00	\N	\N	\N	\N	350	\N	\N
351	2019-01-09 04:45:25.351699+00	2019-01-09 04:45:25.351715+00	\N	\N	\N	\N	351	\N	\N
352	2019-01-09 04:45:25.385146+00	2019-01-09 04:45:25.385167+00	\N	\N	\N	\N	352	\N	\N
353	2019-01-09 04:45:25.425548+00	2019-01-09 04:45:25.425568+00	\N	\N	\N	\N	353	\N	\N
354	2019-01-09 04:45:25.462763+00	2019-01-09 04:45:25.46278+00	\N	\N	\N	\N	354	\N	\N
355	2019-01-09 04:45:25.495648+00	2019-01-09 04:45:25.495664+00	\N	\N	\N	\N	355	\N	\N
356	2019-01-09 04:45:25.532184+00	2019-01-09 04:45:25.532202+00	\N	\N	\N	\N	356	\N	\N
357	2019-01-09 04:45:25.563741+00	2019-01-09 04:45:25.563755+00	\N	\N	\N	\N	357	\N	\N
358	2019-01-09 04:45:25.597116+00	2019-01-09 04:45:25.597131+00	\N	\N	\N	\N	358	\N	\N
359	2019-01-09 04:45:25.631881+00	2019-01-09 04:45:25.631897+00	\N	\N	\N	\N	359	\N	\N
360	2019-01-09 04:45:25.665113+00	2019-01-09 04:45:25.665128+00	\N	\N	\N	\N	360	\N	\N
361	2019-01-09 04:45:25.697841+00	2019-01-09 04:45:25.697855+00	\N	\N	\N	\N	361	\N	\N
362	2019-01-09 04:45:25.730144+00	2019-01-09 04:45:25.73016+00	\N	\N	\N	\N	362	\N	\N
363	2019-01-09 04:45:25.761469+00	2019-01-09 04:45:25.761483+00	\N	\N	\N	\N	363	\N	\N
364	2019-01-09 04:45:25.793664+00	2019-01-09 04:45:25.79368+00	\N	\N	\N	\N	364	\N	\N
365	2019-01-09 04:45:25.824877+00	2019-01-09 04:45:25.824894+00	\N	\N	\N	\N	365	\N	\N
366	2019-01-09 04:45:25.858803+00	2019-01-09 04:45:25.858824+00	\N	\N	\N	\N	366	\N	\N
367	2019-01-09 04:45:25.890273+00	2019-01-09 04:45:25.890287+00	\N	\N	\N	\N	367	\N	\N
368	2019-01-09 04:45:25.920655+00	2019-01-09 04:45:25.920669+00	\N	\N	\N	\N	368	\N	\N
369	2019-01-09 04:45:25.952456+00	2019-01-09 04:45:25.95247+00	\N	\N	\N	\N	369	\N	\N
370	2019-01-09 04:45:25.986267+00	2019-01-09 04:45:25.986281+00	\N	\N	\N	\N	370	\N	\N
371	2019-01-09 04:45:26.044272+00	2019-01-09 04:45:26.044291+00	\N	\N	\N	\N	371	\N	\N
372	2019-01-09 04:45:26.075235+00	2019-01-09 04:45:26.07525+00	\N	\N	\N	\N	372	\N	\N
373	2019-01-09 04:45:26.116685+00	2019-01-09 04:45:26.116698+00	\N	\N	\N	\N	373	\N	\N
374	2019-01-09 04:45:26.148707+00	2019-01-09 04:45:26.148721+00	\N	\N	\N	\N	374	\N	\N
375	2019-01-09 04:45:26.178745+00	2019-01-09 04:45:26.178759+00	\N	\N	\N	\N	375	\N	\N
376	2019-01-09 04:45:26.209026+00	2019-01-09 04:45:26.20904+00	\N	\N	\N	\N	376	\N	\N
377	2019-01-09 04:45:26.239596+00	2019-01-09 04:45:26.23961+00	\N	\N	\N	\N	377	\N	\N
378	2019-01-09 04:45:26.270004+00	2019-01-09 04:45:26.270018+00	\N	\N	\N	\N	378	\N	\N
379	2019-01-09 04:45:26.30218+00	2019-01-09 04:45:26.302194+00	\N	\N	\N	\N	379	\N	\N
380	2019-01-09 04:45:26.333739+00	2019-01-09 04:45:26.333755+00	\N	\N	\N	\N	380	\N	\N
381	2019-01-09 09:44:04.344913+00	2019-01-09 09:44:04.344933+00	\N	\N	\N	\N	381	\N	\N
382	2019-01-09 09:44:04.380056+00	2019-01-09 09:44:04.380073+00	\N	\N	\N	\N	382	\N	\N
383	2019-01-09 09:44:04.413196+00	2019-01-09 09:44:04.413213+00	\N	\N	\N	\N	383	\N	\N
384	2019-01-09 09:44:04.446679+00	2019-01-09 09:44:04.446701+00	\N	\N	\N	\N	384	\N	\N
385	2019-01-09 09:44:04.480637+00	2019-01-09 09:44:04.480655+00	\N	\N	\N	\N	385	\N	\N
386	2019-01-09 09:44:04.515291+00	2019-01-09 09:44:04.51531+00	\N	\N	\N	\N	386	\N	\N
387	2019-01-09 09:44:04.548076+00	2019-01-09 09:44:04.54809+00	\N	\N	\N	\N	387	\N	\N
388	2019-01-09 09:44:04.580172+00	2019-01-09 09:44:04.580188+00	\N	\N	\N	\N	388	\N	\N
\.


--
-- Data for Name: products_productprice; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productprice (id, mrp, price_to_service_partner, price_to_retailer, price_to_super_retailer, start_date, end_date, created_at, modified_at, status, area_id, city_id, product_id, shop_id) FROM stdin;
1	164	141.639999999999986	141.639999999999986	141.639999999999986	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.461689+00	2019-01-08 12:03:42.461707+00	t	\N	1	28	1
2	36	31.4200000000000017	31.4200000000000017	31.4200000000000017	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.466768+00	2019-01-08 12:03:42.46678+00	t	\N	1	29	1
3	84	69.7099999999999937	69.7099999999999937	69.7099999999999937	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.47054+00	2019-01-08 12:03:42.470552+00	t	\N	1	30	1
4	84	69.7099999999999937	69.7099999999999937	69.7099999999999937	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.474376+00	2019-01-08 12:03:42.474388+00	t	\N	1	31	1
5	78	64.730000000000004	64.730000000000004	64.730000000000004	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.478088+00	2019-01-08 12:03:42.478099+00	t	\N	1	32	1
6	80	66.4000000000000057	66.4000000000000057	66.4000000000000057	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.481914+00	2019-01-08 12:03:42.481925+00	t	\N	1	33	1
7	156	129.47999999999999	129.47999999999999	129.47999999999999	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.48572+00	2019-01-08 12:03:42.485731+00	t	\N	1	34	1
8	82	71.5699999999999932	71.5699999999999932	71.5699999999999932	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.489332+00	2019-01-08 12:03:42.489343+00	t	\N	1	35	1
9	82	70.519999999999996	70.519999999999996	70.519999999999996	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.493087+00	2019-01-08 12:03:42.493098+00	t	\N	1	36	1
10	82	68.0600000000000023	68.0600000000000023	68.0600000000000023	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.496849+00	2019-01-08 12:03:42.496861+00	t	\N	1	37	1
11	168	144.47999999999999	144.47999999999999	144.47999999999999	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.500556+00	2019-01-08 12:03:42.500568+00	t	\N	1	38	1
12	160	132.800000000000011	132.800000000000011	132.800000000000011	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.504091+00	2019-01-08 12:03:42.504102+00	t	\N	1	39	1
13	160	132.800000000000011	132.800000000000011	132.800000000000011	2019-01-08 12:01:24+00	2019-02-07 12:01:24+00	2019-01-08 12:03:42.507667+00	2019-01-08 12:03:42.507678+00	t	\N	1	40	1
\.


--
-- Data for Name: products_productpricecsv; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productpricecsv (id, file, uploaded_at, area_id, city_id, country_id, states_id) FROM stdin;
\.


--
-- Data for Name: products_productskugenerator; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productskugenerator (id, parent_cat_sku_code, cat_sku_code, brand_sku_code, last_auto_increment) FROM stdin;
1	HLD	BTC	HRP	00000001
2	HLD	BTC	HRP	00000002
3	HLD	BTC	HRP	00000003
4	HLD	BTC	HRP	00000004
5	HLD	BTC	HRP	00000005
6	HLD	BTC	HRP	00000006
7	HLD	BTC	HRP	00000007
8	HLD	BTC	HRP	00000008
9	HLD	BTC	HRP	00000009
10	HLD	BTC	HRP	00000010
11	HLD	BTC	HRP	00000011
12	HLD	BTC	HRP	00000012
13	HLD	BTC	HRP	00000013
14	HLD	BTC	HRP	00000014
15	HLD	BTC	HRP	00000015
16	HLD	BTC	HRP	00000016
17	HLD	BTC	HRP	00000017
18	HLD	BTC	HRP	00000018
19	HLD	BTC	HRP	00000019
20	HLD	BTC	HRP	00000020
21	HLD	BTC	HRP	00000021
22	HLD	BTC	HRP	00000022
23	HLD	BTC	HRP	00000023
24	HLD	BTC	HRP	00000024
25	HLD	BTC	HRP	00000025
26	HLD	BTC	HRP	00000026
27	HLD	BTC	HRP	00000027
28	HLD	BTC	HRP	00000028
29	HLD	BTC	HRP	00000029
30	HLD	BTC	HRP	00000030
31	HLD	BTC	HRP	00000031
32	HLD	BTC	HRP	00000032
33	HLD	BTC	HRP	00000033
34	HLD	BTC	HRP	00000034
35	HLD	BTC	HRP	00000035
36	HLD	BTC	HRP	00000036
37	HLD	BTC	HRP	00000037
38	HLD	BTC	HRP	00000038
39	HLD	BTC	HRP	00000039
40	HLD	BTC	HRP	00000040
41	HLD	SHC	CHR	00000001
42	HLD	SHC	CHR	00000002
43	PCR	HRC	CLI	00000001
44	PCR	ORC	CLP	00000001
45	PCR	ORC	CLB	00000001
46	PCR	ORC	CLB	00000002
47	PCR	ORC	CLB	00000003
48	PCR	ORC	CLB	00000004
49	PCR	ORC	CLB	00000005
50	PCR	ORC	CLB	00000006
51	PCR	ORC	CLB	00000007
52	PCR	ORC	CLB	00000008
53	PCR	ORC	CLB	00000009
54	PCR	ORC	CLB	00000010
55	PCR	ORC	CLB	00000011
56	HLD	GLC	CLN	00000001
57	HLD	GLC	CLN	00000002
58	PCR	HRC	DAL	00000001
59	PCR	HRC	DAM	00000001
60	PCR	HRC	DAM	00000002
61	PCR	ORC	DRE	00000001
62	PCR	ORC	DRE	00000002
63	PCR	ORC	DRE	00000003
64	PCR	HWS	DET	00000001
65	PCR	BBS	DET	00000001
66	PCR	BBS	DET	00000002
67	PCR	BBS	DET	00000003
68	PCR	SVN	DET	00000001
69	PCR	SVN	DET	00000002
70	PCR	BBS	DET	00000004
71	PCR	BBS	DET	00000005
72	PCR	BBS	DET	00000006
73	PCR	BBS	DET	00000007
74	PCR	HWS	DET	00000002
75	PCR	HWS	DET	00000003
76	PCR	HWS	DET	00000004
77	HLD	DWS	DET	00000001
78	HLD	DWS	DET	00000002
79	PCR	HWS	DET	00000005
80	PCR	BBS	DET	00000008
81	PCR	HWS	DET	00000006
82	HLD	DWS	DET	00000003
83	HLD	DWS	DET	00000004
84	PCR	HWS	DET	00000007
85	PCR	BBS	DET	00000009
86	PCR	BBS	DET	00000010
87	PCR	BBS	DET	00000011
88	PCR	BBS	DET	00000012
89	PCR	BBS	DET	00000013
90	PCR	BBS	DET	00000014
91	PCR	HWS	DET	00000008
92	PCR	BBS	DOV	00000001
93	PCR	HRC	DOV	00000001
94	PCR	HRC	DOV	00000002
95	PCR	HRC	DOV	00000003
96	PCR	HRC	DOV	00000004
97	PCR	HRC	DOV	00000005
98	PCR	DEO	ENG	00000001
99	PCR	DEO	ENG	00000002
100	PCR	DEO	ENG	00000003
101	PCR	SKC	FAL	00000001
102	PCR	SKC	FAL	00000002
103	PCR	SKC	FAL	00000003
104	HLD	DET	FNA	00000001
105	HLD	DET	FNA	00000002
106	HLD	DET	FNA	00000003
107	HLD	DET	FNA	00000004
108	HLD	DET	GHD	00000001
109	HLD	DET	GHD	00000002
110	HLD	DET	GHD	00000003
111	HLD	DET	GHD	00000004
112	HLD	DET	GHD	00000005
113	PCR	SVN	GIL	00000001
114	PCR	SVN	GIL	00000002
115	PCR	HRC	GEX	00000001
116	PCR	HRC	GEX	00000002
117	PCR	HRC	GEX	00000003
118	PCR	HRC	GEX	00000004
119	HLD	DET	EZE	00000001
120	HLD	DET	EZE	00000002
121	HLD	DET	EZE	00000003
122	PCR	BBS	GNO	00000001
123	PCR	BBS	GNO	00000002
124	PCR	BBS	GNO	00000003
125	PCR	BBS	GNO	00000004
126	PCR	BBS	GNO	00000005
127	PCR	BBS	GNO	00000006
128	PCR	BBS	GNO	00000007
129	PCR	BBS	GNO	00000008
130	PCR	BBS	GNO	00000009
131	PCR	BBS	GNO	00000010
132	PCR	BBS	GNO	00000011
133	PCR	BBS	GNO	00000012
134	PCR	BBS	GNO	00000013
135	PCR	BBS	GNO	00000014
136	PCR	BBS	GNO	00000015
137	PCR	BBS	GNO	00000016
138	PCR	BBS	GNO	00000017
139	PCR	HRC	GNU	00000001
140	PCR	HRC	GNU	00000002
141	PCR	HRC	GNU	00000003
142	HLD	MQR	GGN	00000001
143	PCR	HRC	HNC	00000001
144	PCR	HRC	HNC	00000002
145	PCR	HRC	HNC	00000003
146	PCR	HRC	HNS	00000001
147	PCR	HRC	HNS	00000002
148	PCR	HRC	HNS	00000003
149	PCR	HRC	HNS	00000004
150	PCR	HRC	HNS	00000005
151	HLD	DET	HER	00000001
152	HLD	DET	HER	00000002
153	PCR	ORC	RED	00000001
154	PCR	BBS	LIF	00000001
155	HLD	BTC	LIZ	00000001
156	HLD	BTC	LIZ	00000002
157	HLD	BTC	LIZ	00000003
158	HLD	BTC	LIZ	00000004
159	HLD	BTC	LIZ	00000005
160	HLD	BTC	LIZ	00000006
161	HLD	BTC	LIZ	00000007
162	HLD	BTC	LIZ	00000008
163	HLD	BTC	LIZ	00000009
164	HLD	BTC	LIZ	00000010
165	HLD	BTC	LIZ	00000011
166	HLD	BTC	LIZ	00000012
167	HLD	BTC	LIZ	00000013
168	HLD	BTC	LIZ	00000014
169	PCR	BBS	LUX	00000001
170	PCR	BBS	LUX	00000002
171	PCR	ORC	DME	00000001
172	PCR	EVM	MOV	00000001
173	PCR	EVM	MOV	00000002
174	PCR	EVM	MOV	00000003
175	PCR	EVM	MOV	00000004
176	PCR	HRC	NIH	00000001
177	PCR	HRC	NIH	00000002
178	HLD	DWS	FNI	00000001
179	HLD	DWS	FNI	00000002
180	HLD	FRS	DOD	00000001
181	HLD	FRS	DOD	00000002
182	HLD	FRS	DOD	00000003
183	HLD	FRS	DOD	00000004
184	HLD	FRS	DOD	00000005
185	HLD	FRS	DOD	00000006
186	PCR	BBC	PAM	00000001
187	PCR	BBC	PAM	00000002
188	PCR	BBC	PAM	00000003
189	PCR	BBC	PAM	00000004
190	PCR	BBC	PAM	00000005
191	PCR	HRC	PAN	00000001
192	PCR	HRC	PAN	00000002
193	PCR	HRC	PAN	00000003
194	PCR	HRC	PAN	00000004
195	PCR	HRC	PAR	00000001
196	PCR	HRC	PAR	00000002
197	PCR	HRC	PAR	00000003
198	PCR	HRC	PAR	00000004
199	PCR	HRC	PAR	00000005
200	PCR	HRC	PAR	00000006
201	PCR	HRC	PAR	00000007
202	HLD	DET	PAT	00000001
203	PCR	BBS	PAT	00000001
204	PCR	BBS	PAT	00000002
205	PCR	HRC	PAT	00000001
206	HLD	DET	PAT	00000002
207	HLD	DET	PAT	00000003
208	HLD	DET	PAT	00000004
209	PCR	ORC	PAT	00000001
210	HLD	DET	PAT	00000005
211	PCR	SKC	PAT	00000001
212	PCR	SKC	PAT	00000002
213	PCR	ORC	PEP	00000001
214	PCR	SKC	PND	00000001
215	HLD	DET	REV	00000001
216	HLD	DET	REV	00000002
217	HLD	DET	REV	00000003
218	HLD	DET	REV	00000004
219	HLD	DET	RIN	00000001
220	HLD	DET	RIN	00000002
221	HLD	DET	RIN	00000003
222	HLD	DET	ROB	00000001
223	PCR	HRC	SWT	00000001
224	PCR	HRC	SWT	00000002
225	PCR	HRC	SWT	00000003
226	PCR	HRC	SWT	00000004
227	PCR	HRC	SWT	00000005
228	PCR	HRC	SWT	00000006
229	PCR	HRC	SWT	00000007
230	PCR	HRC	SWT	00000008
231	PCR	HRC	SWT	00000009
232	PCR	HRC	SUN	00000001
233	PCR	HRC	SUN	00000002
234	HLD	DET	SRF	00000001
235	HLD	DET	SRF	00000002
236	HLD	DET	SRF	00000003
237	HLD	DET	SRF	00000004
238	HLD	DET	SRF	00000005
239	HLD	DET	TID	00000001
240	HLD	DET	TID	00000002
241	HLD	DET	TID	00000003
242	HLD	DET	TID	00000004
243	PCR	HRC	TRE	00000001
244	PCR	HRC	TRE	00000002
245	PCR	HRC	TRE	00000003
246	HLD	DET	VAN	00000001
247	PCR	SKC	VAS	00000001
248	PCR	HRM	VET	00000001
249	PCR	HRM	VET	00000002
250	PCR	HRM	VET	00000003
251	PCR	HRM	VET	00000004
252	PCR	HRM	VET	00000005
253	PCR	HRM	VET	00000006
254	PCR	HRM	VET	00000007
255	PCR	HRM	VET	00000008
256	PCR	EVM	VIC	00000001
257	HLD	DWS	VIM	00000001
258	HLD	DWS	VIM	00000002
259	HLD	DWS	VIM	00000003
260	HLD	DWS	VIM	00000004
261	PCR	BBS	VIV	00000001
262	HLD	DET	WHE	00000001
263	HLD	DET	WHE	00000002
264	PCR	SNT	WSP	00000001
265	PCR	SNT	WSP	00000002
266	PCR	SNT	WSP	00000003
267	PCR	SKC	VAS	00000002
268	HLD	DET	WHE	00000003
269	HLD	DET	WHE	00000004
270	SBF	NPV	MAG	00000001
271	SBF	KSC	MAG	00000001
272	DAY	PWM	EVD	00000001
273	INF	BBF	CER	00000001
274	INF	BBF	LAC	00000001
275	INF	BBF	LAC	00000002
276	SBF	NPV	MAG	00000002
277	SBF	NPV	MAG	00000003
278	SBF	NPV	MAG	00000004
279	INF	BBF	CER	00000002
280	INF	BBF	CER	00000003
281	INF	BBF	CER	00000004
282	INF	BBF	LAC	00000003
283	INF	BBF	LAC	00000004
284	INF	BBF	LAC	00000005
285	SBF	KSC	MAG	00000002
286	SBF	BAC	SNF	00000001
287	SBF	BAC	SNF	00000002
288	SBF	CNN	BNG	00000001
289	SBF	CNN	BNG	00000002
290	SBF	CNN	BNG	00000003
291	SBF	BAC	SNF	00000003
292	SBF	NPV	YIP	00000001
293	SBF	BAC	YIP	00000001
294	SBF	BAC	SNF	00000004
295	SBF	BAC	SNF	00000005
296	SBF	BAC	SNF	00000006
297	SBF	NPV	YIP	00000002
298	SBF	BAC	SNF	00000007
299	SBF	BAC	SNF	00000008
300	SBF	BAC	SNF	00000009
301	SBF	BAC	SNF	00000010
302	SBF	BAC	SNF	00000011
303	SBF	BAC	SNF	00000012
304	SBF	BAC	SNF	00000013
305	SBF	BAC	SNF	00000014
306	SBF	BAC	SNF	00000015
307	SBF	BAC	SNF	00000016
308	SBF	BAC	SNF	00000017
309	SBF	CNN	BNG	00000004
310	SBF	CNN	BNG	00000005
311	SBF	CNN	BNG	00000006
312	SBF	CNN	BNG	00000007
313	SBF	CNN	BNG	00000008
314	SBF	CNN	BNG	00000009
315	SBF	CNN	BNG	00000010
316	SBF	CNN	BNG	00000011
317	SBF	BFC	CNF	00000001
318	SBF	BFC	CNF	00000002
319	SBF	BFC	CNF	00000003
320	SBF	BFC	CNF	00000004
321	SBF	BFC	CHO	00000001
322	SBF	BFC	CHO	00000002
323	SBF	BFC	CHO	00000003
324	SBF	BFC	CHO	00000004
325	SBF	BFC	CHO	00000005
326	SBF	BFC	CHO	00000006
327	SBF	BFC	CHO	00000007
328	SBF	BFC	CHO	00000008
329	SBF	BFC	CHO	00000009
330	SBF	CNN	LAY	00000001
331	SBF	CNN	LAY	00000002
332	SBF	CNN	LAY	00000003
333	SBF	CNN	LAY	00000004
334	SBF	CNN	LAY	00000005
335	SBF	CNN	DOR	00000001
336	SBF	CNN	DOR	00000002
337	SBF	CNN	LAY	00000006
338	SBF	CNN	LAY	00000007
339	SBF	CNN	LAY	00000008
340	SBF	CNN	LAY	00000009
341	SBF	BFC	QKR	00000001
342	SBF	CNN	HAS	00000001
343	SBF	CNN	HAS	00000002
344	SBF	CNN	HAS	00000003
345	SBF	CNN	HAS	00000004
346	SBF	CNN	HAS	00000005
347	SBF	CNN	HAS	00000006
348	SBF	CNN	HAS	00000007
349	SBF	CNN	HAS	00000008
350	SBF	CNN	HAS	00000009
351	SBF	CNN	HAS	00000010
352	SBF	CNN	HAS	00000011
353	SBF	CNN	HAS	00000012
354	SBF	CNN	HAS	00000013
355	SBF	CNN	HAS	00000014
356	SBF	CNN	HAS	00000015
357	SBF	CNN	HAS	00000016
358	SBF	CNN	HAS	00000017
359	SBF	CNN	HAS	00000018
360	SBF	CNN	HAS	00000019
361	SBF	CNN	HAS	00000020
362	SBF	CNN	HAS	00000021
363	SBF	CNN	HAS	00000022
364	SBF	CNN	HAS	00000023
365	SBF	CNN	HAS	00000024
366	SBF	CNN	HAS	00000025
367	SBF	CNN	HAS	00000026
368	SBF	CNN	HAS	00000027
369	SBF	CNN	HAS	00000028
370	SBF	CNN	HAS	00000029
371	SBF	CNN	HAS	00000030
372	SBF	BFC	SOA	00000001
373	SBF	BFC	SOA	00000002
374	SBF	BFC	SOA	00000003
375	SBF	BFC	SOA	00000004
376	SBF	BFC	SOA	00000005
377	SBF	BFC	SOA	00000006
378	SBF	BFC	SOA	00000007
379	SBF	BFC	SOA	00000008
380	SBF	BFC	SOA	00000009
381	HLD	DET	TID	00000005
382	HLD	DET	TID	00000006
383	HLD	DET	RIN	00000004
384	HLD	DET	TID	00000007
385	HLD	DET	TID	00000008
386	HLD	DWS	VIM	00000005
387	HLD	DWS	VIM	00000006
388	HLD	DWS	VIM	00000007
389	HLD	DET	TID	00000009
390	HLD	DWS	TID	00000001
\.


--
-- Data for Name: products_producttaxmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_producttaxmapping (id, created_at, modified_at, status, product_id, tax_id) FROM stdin;
28	2019-01-08 08:24:54.467523+00	2019-01-08 08:24:54.467537+00	t	28	4
29	2019-01-08 08:24:54.498776+00	2019-01-08 08:24:54.49879+00	t	29	4
30	2019-01-08 08:24:54.530133+00	2019-01-08 08:24:54.530147+00	t	30	4
31	2019-01-08 08:24:54.561953+00	2019-01-08 08:24:54.56197+00	t	31	4
32	2019-01-08 08:24:54.593431+00	2019-01-08 08:24:54.593445+00	t	32	4
33	2019-01-08 08:24:54.624465+00	2019-01-08 08:24:54.62448+00	t	33	4
34	2019-01-08 08:24:54.6554+00	2019-01-08 08:24:54.655419+00	t	34	4
35	2019-01-08 08:24:54.687152+00	2019-01-08 08:24:54.687167+00	t	35	4
36	2019-01-08 08:24:54.718158+00	2019-01-08 08:24:54.718171+00	t	36	4
37	2019-01-08 08:24:54.748294+00	2019-01-08 08:24:54.748308+00	t	37	4
38	2019-01-08 08:24:54.778778+00	2019-01-08 08:24:54.778792+00	t	38	4
39	2019-01-08 08:24:54.809134+00	2019-01-08 08:24:54.809148+00	t	39	4
40	2019-01-08 08:24:54.86058+00	2019-01-08 08:24:54.860595+00	t	40	4
41	2019-01-08 14:12:04.058002+00	2019-01-08 14:12:04.05802+00	t	41	4
42	2019-01-08 14:12:04.096438+00	2019-01-08 14:12:04.096452+00	t	42	4
43	2019-01-08 14:12:04.130184+00	2019-01-08 14:12:04.130198+00	t	43	4
44	2019-01-08 14:12:04.169914+00	2019-01-08 14:12:04.169932+00	t	44	4
45	2019-01-08 14:12:04.20303+00	2019-01-08 14:12:04.203049+00	t	45	4
46	2019-01-08 14:12:04.242791+00	2019-01-08 14:12:04.24281+00	t	46	4
47	2019-01-08 14:12:04.277088+00	2019-01-08 14:12:04.277106+00	t	47	4
48	2019-01-08 14:12:04.314867+00	2019-01-08 14:12:04.314884+00	t	48	4
49	2019-01-08 14:12:04.348948+00	2019-01-08 14:12:04.348966+00	t	49	4
50	2019-01-08 14:12:04.382837+00	2019-01-08 14:12:04.382852+00	t	50	4
51	2019-01-08 14:12:04.416058+00	2019-01-08 14:12:04.416075+00	t	51	4
52	2019-01-08 14:12:04.452367+00	2019-01-08 14:12:04.452381+00	t	52	4
53	2019-01-08 14:12:04.485679+00	2019-01-08 14:12:04.485694+00	t	53	4
54	2019-01-08 14:12:04.520688+00	2019-01-08 14:12:04.520702+00	t	54	4
55	2019-01-08 14:12:04.555006+00	2019-01-08 14:12:04.555021+00	t	55	4
56	2019-01-08 14:12:04.587242+00	2019-01-08 14:12:04.587258+00	t	56	4
57	2019-01-08 14:12:04.618927+00	2019-01-08 14:12:04.618942+00	t	57	4
58	2019-01-08 14:12:04.651759+00	2019-01-08 14:12:04.651775+00	t	58	4
59	2019-01-08 14:12:04.68627+00	2019-01-08 14:12:04.686285+00	t	59	4
60	2019-01-08 14:12:04.720016+00	2019-01-08 14:12:04.720033+00	t	60	4
61	2019-01-08 14:12:04.753273+00	2019-01-08 14:12:04.753288+00	t	61	4
62	2019-01-08 14:12:04.785978+00	2019-01-08 14:12:04.785995+00	t	62	4
63	2019-01-08 14:12:04.821559+00	2019-01-08 14:12:04.821586+00	t	63	4
64	2019-01-08 14:12:04.859901+00	2019-01-08 14:12:04.859923+00	t	64	4
65	2019-01-08 14:12:04.89606+00	2019-01-08 14:12:04.896076+00	t	65	4
66	2019-01-08 14:12:04.931018+00	2019-01-08 14:12:04.931033+00	t	66	4
67	2019-01-08 14:12:04.963915+00	2019-01-08 14:12:04.963931+00	t	67	4
68	2019-01-08 14:12:04.997595+00	2019-01-08 14:12:04.997612+00	t	68	4
69	2019-01-08 14:12:05.061802+00	2019-01-08 14:12:05.061817+00	t	69	4
70	2019-01-08 14:12:05.097148+00	2019-01-08 14:12:05.097166+00	t	70	4
71	2019-01-08 14:12:05.129174+00	2019-01-08 14:12:05.129191+00	t	71	4
72	2019-01-08 14:12:05.162347+00	2019-01-08 14:12:05.162362+00	t	72	4
73	2019-01-08 14:12:05.195216+00	2019-01-08 14:12:05.195232+00	t	73	4
74	2019-01-08 14:12:05.229254+00	2019-01-08 14:12:05.22927+00	t	74	4
75	2019-01-08 14:12:05.263043+00	2019-01-08 14:12:05.263061+00	t	75	4
76	2019-01-08 14:12:05.296294+00	2019-01-08 14:12:05.296308+00	t	76	4
77	2019-01-08 14:12:05.331423+00	2019-01-08 14:12:05.331439+00	t	77	4
78	2019-01-08 14:12:05.363848+00	2019-01-08 14:12:05.363863+00	t	78	4
79	2019-01-08 14:12:05.407732+00	2019-01-08 14:12:05.407755+00	t	79	4
80	2019-01-08 14:12:05.441243+00	2019-01-08 14:12:05.441259+00	t	80	4
81	2019-01-08 14:12:05.473588+00	2019-01-08 14:12:05.473604+00	t	81	4
82	2019-01-08 14:12:05.505289+00	2019-01-08 14:12:05.505304+00	t	82	4
83	2019-01-08 14:12:05.537999+00	2019-01-08 14:12:05.538017+00	t	83	4
84	2019-01-08 14:12:05.570338+00	2019-01-08 14:12:05.570353+00	t	84	4
85	2019-01-08 14:12:05.603219+00	2019-01-08 14:12:05.603236+00	t	85	4
86	2019-01-08 14:12:05.639891+00	2019-01-08 14:12:05.63991+00	t	86	4
87	2019-01-08 14:12:05.671327+00	2019-01-08 14:12:05.671343+00	t	87	4
88	2019-01-08 14:12:05.706615+00	2019-01-08 14:12:05.706631+00	t	88	4
89	2019-01-08 14:12:05.741301+00	2019-01-08 14:12:05.741317+00	t	89	4
90	2019-01-08 14:12:05.778679+00	2019-01-08 14:12:05.778694+00	t	90	4
91	2019-01-08 14:12:05.816071+00	2019-01-08 14:12:05.816088+00	t	91	4
92	2019-01-08 14:12:05.85043+00	2019-01-08 14:12:05.850447+00	t	92	4
93	2019-01-08 14:12:05.882716+00	2019-01-08 14:12:05.882737+00	t	93	4
94	2019-01-08 14:12:05.915366+00	2019-01-08 14:12:05.915381+00	t	94	4
95	2019-01-08 14:12:05.946827+00	2019-01-08 14:12:05.946843+00	t	95	4
96	2019-01-08 14:12:05.980395+00	2019-01-08 14:12:05.980409+00	t	96	4
97	2019-01-08 14:12:06.019412+00	2019-01-08 14:12:06.019429+00	t	97	4
98	2019-01-08 14:12:06.05372+00	2019-01-08 14:12:06.053738+00	t	98	4
99	2019-01-08 14:12:06.087211+00	2019-01-08 14:12:06.087228+00	t	99	4
100	2019-01-08 14:12:06.12287+00	2019-01-08 14:12:06.122888+00	t	100	4
101	2019-01-08 14:12:06.154346+00	2019-01-08 14:12:06.154365+00	t	101	4
102	2019-01-08 14:12:06.186504+00	2019-01-08 14:12:06.186518+00	t	102	4
103	2019-01-08 14:12:06.218596+00	2019-01-08 14:12:06.218611+00	t	103	4
104	2019-01-08 14:12:06.250678+00	2019-01-08 14:12:06.250692+00	t	104	4
105	2019-01-08 14:12:06.28363+00	2019-01-08 14:12:06.283644+00	t	105	4
106	2019-01-08 14:12:06.315885+00	2019-01-08 14:12:06.315901+00	t	106	4
107	2019-01-08 14:12:06.349964+00	2019-01-08 14:12:06.349979+00	t	107	4
108	2019-01-08 14:12:06.383267+00	2019-01-08 14:12:06.383286+00	t	108	4
109	2019-01-08 14:12:06.41654+00	2019-01-08 14:12:06.416559+00	t	109	4
110	2019-01-08 14:12:06.448853+00	2019-01-08 14:12:06.448869+00	t	110	4
111	2019-01-08 14:12:06.483565+00	2019-01-08 14:12:06.483585+00	t	111	4
112	2019-01-08 14:12:06.515281+00	2019-01-08 14:12:06.515296+00	t	112	4
113	2019-01-08 14:12:06.547201+00	2019-01-08 14:12:06.547216+00	t	113	4
114	2019-01-08 14:12:06.579002+00	2019-01-08 14:12:06.579017+00	t	114	4
115	2019-01-08 14:12:06.610538+00	2019-01-08 14:12:06.610556+00	t	115	4
116	2019-01-08 14:12:06.641469+00	2019-01-08 14:12:06.641486+00	t	116	4
117	2019-01-08 14:12:06.672974+00	2019-01-08 14:12:06.672991+00	t	117	4
118	2019-01-08 14:12:06.711217+00	2019-01-08 14:12:06.711242+00	t	118	4
119	2019-01-08 14:12:06.748152+00	2019-01-08 14:12:06.748169+00	t	119	4
120	2019-01-08 14:12:06.779935+00	2019-01-08 14:12:06.779952+00	t	120	4
121	2019-01-08 14:12:06.811679+00	2019-01-08 14:12:06.811694+00	t	121	4
122	2019-01-08 14:12:06.843491+00	2019-01-08 14:12:06.843514+00	t	122	4
123	2019-01-08 14:12:06.876381+00	2019-01-08 14:12:06.876395+00	t	123	4
124	2019-01-08 14:12:06.908664+00	2019-01-08 14:12:06.908683+00	t	124	4
125	2019-01-08 14:12:06.940172+00	2019-01-08 14:12:06.940186+00	t	125	4
126	2019-01-08 14:12:06.972174+00	2019-01-08 14:12:06.972191+00	t	126	4
127	2019-01-08 14:12:07.003975+00	2019-01-08 14:12:07.003993+00	t	127	4
128	2019-01-08 14:12:07.035918+00	2019-01-08 14:12:07.035934+00	t	128	4
129	2019-01-08 14:12:07.067768+00	2019-01-08 14:12:07.067783+00	t	129	4
130	2019-01-08 14:12:07.099411+00	2019-01-08 14:12:07.099426+00	t	130	4
131	2019-01-08 14:12:07.131449+00	2019-01-08 14:12:07.131464+00	t	131	4
132	2019-01-08 14:12:07.163363+00	2019-01-08 14:12:07.163378+00	t	132	4
133	2019-01-08 14:12:07.195233+00	2019-01-08 14:12:07.195252+00	t	133	4
134	2019-01-08 14:12:07.228754+00	2019-01-08 14:12:07.228771+00	t	134	4
135	2019-01-08 14:12:07.261046+00	2019-01-08 14:12:07.261068+00	t	135	4
136	2019-01-08 14:12:07.292473+00	2019-01-08 14:12:07.292488+00	t	136	4
137	2019-01-08 14:12:07.324528+00	2019-01-08 14:12:07.324545+00	t	137	4
138	2019-01-08 14:12:07.357164+00	2019-01-08 14:12:07.357178+00	t	138	4
139	2019-01-08 14:12:07.389423+00	2019-01-08 14:12:07.389437+00	t	139	4
140	2019-01-08 14:12:07.420787+00	2019-01-08 14:12:07.420805+00	t	140	4
141	2019-01-08 14:12:07.45417+00	2019-01-08 14:12:07.454184+00	t	141	4
142	2019-01-08 14:12:07.485238+00	2019-01-08 14:12:07.485256+00	t	142	4
143	2019-01-08 14:12:07.517888+00	2019-01-08 14:12:07.517903+00	t	143	4
144	2019-01-08 14:12:07.550499+00	2019-01-08 14:12:07.550516+00	t	144	4
145	2019-01-08 14:12:07.582989+00	2019-01-08 14:12:07.583013+00	t	145	4
146	2019-01-08 14:12:07.615232+00	2019-01-08 14:12:07.615249+00	t	146	4
147	2019-01-08 14:12:07.647597+00	2019-01-08 14:12:07.647614+00	t	147	4
148	2019-01-08 14:12:07.679964+00	2019-01-08 14:12:07.679985+00	t	148	4
149	2019-01-08 14:12:07.712095+00	2019-01-08 14:12:07.712115+00	t	149	4
150	2019-01-08 14:12:07.743475+00	2019-01-08 14:12:07.743493+00	t	150	4
151	2019-01-08 14:12:07.77516+00	2019-01-08 14:12:07.775176+00	t	151	4
152	2019-01-08 14:12:07.808602+00	2019-01-08 14:12:07.808619+00	t	152	4
153	2019-01-08 14:12:07.840034+00	2019-01-08 14:12:07.84005+00	t	153	3
154	2019-01-08 14:12:07.873292+00	2019-01-08 14:12:07.873313+00	t	154	4
155	2019-01-08 14:12:07.904725+00	2019-01-08 14:12:07.904742+00	t	155	4
156	2019-01-08 14:12:07.936799+00	2019-01-08 14:12:07.936814+00	t	156	4
157	2019-01-08 14:12:07.968261+00	2019-01-08 14:12:07.968277+00	t	157	4
158	2019-01-08 14:12:07.999843+00	2019-01-08 14:12:07.999858+00	t	158	4
159	2019-01-08 14:12:08.035587+00	2019-01-08 14:12:08.035604+00	t	159	4
160	2019-01-08 14:12:08.067665+00	2019-01-08 14:12:08.06768+00	t	160	4
161	2019-01-08 14:12:08.101036+00	2019-01-08 14:12:08.101059+00	t	161	4
162	2019-01-08 14:12:08.13471+00	2019-01-08 14:12:08.134729+00	t	162	4
163	2019-01-08 14:12:08.167521+00	2019-01-08 14:12:08.167538+00	t	163	4
164	2019-01-08 14:12:08.200274+00	2019-01-08 14:12:08.200297+00	t	164	4
165	2019-01-08 14:12:08.232903+00	2019-01-08 14:12:08.232924+00	t	165	4
166	2019-01-08 14:12:08.266555+00	2019-01-08 14:12:08.266573+00	t	166	4
167	2019-01-08 14:12:08.298217+00	2019-01-08 14:12:08.298233+00	t	167	4
168	2019-01-08 14:12:08.330584+00	2019-01-08 14:12:08.330603+00	t	168	4
169	2019-01-08 14:12:08.364747+00	2019-01-08 14:12:08.36478+00	t	169	4
170	2019-01-08 14:12:08.397234+00	2019-01-08 14:12:08.397255+00	t	170	4
171	2019-01-08 14:12:08.428726+00	2019-01-08 14:12:08.428743+00	t	171	4
172	2019-01-08 14:12:08.460925+00	2019-01-08 14:12:08.460949+00	t	172	3
173	2019-01-08 14:12:08.500156+00	2019-01-08 14:12:08.500184+00	t	173	3
174	2019-01-08 14:12:08.533238+00	2019-01-08 14:12:08.533263+00	t	174	3
175	2019-01-08 14:12:08.56713+00	2019-01-08 14:12:08.567158+00	t	175	3
176	2019-01-08 14:12:08.601083+00	2019-01-08 14:12:08.601109+00	t	176	4
177	2019-01-08 14:12:08.634392+00	2019-01-08 14:12:08.634418+00	t	177	4
178	2019-01-08 14:12:08.667605+00	2019-01-08 14:12:08.667622+00	t	178	4
179	2019-01-08 14:12:08.700778+00	2019-01-08 14:12:08.700794+00	t	179	4
180	2019-01-08 14:12:08.733405+00	2019-01-08 14:12:08.733428+00	t	180	4
181	2019-01-08 14:12:08.765036+00	2019-01-08 14:12:08.765052+00	t	181	4
182	2019-01-08 14:12:08.796474+00	2019-01-08 14:12:08.796492+00	t	182	4
183	2019-01-08 14:12:08.829858+00	2019-01-08 14:12:08.829882+00	t	183	4
184	2019-01-08 14:12:08.861909+00	2019-01-08 14:12:08.861923+00	t	184	4
185	2019-01-08 14:12:08.893871+00	2019-01-08 14:12:08.893887+00	t	185	4
186	2019-01-08 14:12:08.925726+00	2019-01-08 14:12:08.92574+00	t	186	3
187	2019-01-08 14:12:08.958546+00	2019-01-08 14:12:08.958562+00	t	187	3
188	2019-01-08 14:12:08.991157+00	2019-01-08 14:12:08.991174+00	t	188	3
189	2019-01-08 14:12:09.025561+00	2019-01-08 14:12:09.025578+00	t	189	3
190	2019-01-08 14:12:09.058238+00	2019-01-08 14:12:09.058259+00	t	190	3
191	2019-01-08 14:12:09.090478+00	2019-01-08 14:12:09.090495+00	t	191	4
192	2019-01-08 14:12:09.124655+00	2019-01-08 14:12:09.124681+00	t	192	4
193	2019-01-08 14:12:09.15682+00	2019-01-08 14:12:09.156841+00	t	193	4
194	2019-01-08 14:12:09.189324+00	2019-01-08 14:12:09.18934+00	t	194	4
195	2019-01-08 14:12:09.220951+00	2019-01-08 14:12:09.220967+00	t	195	4
196	2019-01-08 14:12:09.251801+00	2019-01-08 14:12:09.251818+00	t	196	2
197	2019-01-08 14:12:09.284242+00	2019-01-08 14:12:09.284258+00	t	197	4
198	2019-01-08 14:12:09.315701+00	2019-01-08 14:12:09.31573+00	t	198	4
199	2019-01-08 14:12:09.347525+00	2019-01-08 14:12:09.347546+00	t	199	4
200	2019-01-08 14:12:09.379338+00	2019-01-08 14:12:09.379353+00	t	200	2
201	2019-01-08 14:12:09.413417+00	2019-01-08 14:12:09.413436+00	t	201	2
202	2019-01-08 14:12:09.445338+00	2019-01-08 14:12:09.445354+00	t	202	4
203	2019-01-08 14:12:09.476572+00	2019-01-08 14:12:09.476589+00	t	203	4
204	2019-01-08 14:12:09.507928+00	2019-01-08 14:12:09.507945+00	t	204	4
205	2019-01-08 14:12:09.538636+00	2019-01-08 14:12:09.538654+00	t	205	4
206	2019-01-08 14:12:09.572486+00	2019-01-08 14:12:09.572504+00	t	206	4
207	2019-01-08 14:12:09.604366+00	2019-01-08 14:12:09.604383+00	t	207	4
208	2019-01-08 14:12:09.637263+00	2019-01-08 14:12:09.637281+00	t	208	4
209	2019-01-08 14:12:09.669897+00	2019-01-08 14:12:09.669916+00	t	209	4
210	2019-01-08 14:12:09.701872+00	2019-01-08 14:12:09.701897+00	t	210	4
211	2019-01-08 14:12:09.734813+00	2019-01-08 14:12:09.734834+00	t	211	4
212	2019-01-08 14:12:09.766575+00	2019-01-08 14:12:09.766588+00	t	212	4
213	2019-01-08 14:12:09.798208+00	2019-01-08 14:12:09.798224+00	t	213	4
214	2019-01-08 14:12:09.830403+00	2019-01-08 14:12:09.830424+00	t	214	4
215	2019-01-08 14:12:09.880028+00	2019-01-08 14:12:09.880047+00	t	215	4
216	2019-01-08 14:12:09.912869+00	2019-01-08 14:12:09.912895+00	t	216	4
217	2019-01-08 14:12:09.946133+00	2019-01-08 14:12:09.946153+00	t	217	4
218	2019-01-08 14:12:09.977848+00	2019-01-08 14:12:09.977863+00	t	218	4
219	2019-01-08 14:12:10.076489+00	2019-01-08 14:12:10.076508+00	t	219	4
220	2019-01-08 14:12:10.108199+00	2019-01-08 14:12:10.108221+00	t	220	4
221	2019-01-08 14:12:10.14089+00	2019-01-08 14:12:10.140907+00	t	221	4
222	2019-01-08 14:12:10.176444+00	2019-01-08 14:12:10.176463+00	t	222	4
223	2019-01-08 14:12:10.212018+00	2019-01-08 14:12:10.212038+00	t	223	4
224	2019-01-08 14:12:10.245064+00	2019-01-08 14:12:10.245085+00	t	224	4
225	2019-01-08 14:12:10.277779+00	2019-01-08 14:12:10.277796+00	t	225	4
226	2019-01-08 14:12:10.31016+00	2019-01-08 14:12:10.310176+00	t	226	4
227	2019-01-08 14:12:10.345853+00	2019-01-08 14:12:10.345886+00	t	227	4
228	2019-01-08 14:12:10.386371+00	2019-01-08 14:12:10.386395+00	t	228	4
229	2019-01-08 14:12:10.421435+00	2019-01-08 14:12:10.421457+00	t	229	4
230	2019-01-08 14:12:10.457731+00	2019-01-08 14:12:10.457747+00	t	230	4
231	2019-01-08 14:12:10.491654+00	2019-01-08 14:12:10.491673+00	t	231	4
232	2019-01-08 14:12:10.530542+00	2019-01-08 14:12:10.530558+00	t	232	4
233	2019-01-08 14:12:10.566995+00	2019-01-08 14:12:10.567016+00	t	233	4
234	2019-01-08 14:12:10.599776+00	2019-01-08 14:12:10.599793+00	t	234	4
235	2019-01-08 14:12:10.634198+00	2019-01-08 14:12:10.634214+00	t	235	4
236	2019-01-08 14:12:10.66956+00	2019-01-08 14:12:10.669576+00	t	236	4
237	2019-01-08 14:12:10.70391+00	2019-01-08 14:12:10.703928+00	t	237	4
238	2019-01-08 14:12:10.73675+00	2019-01-08 14:12:10.736767+00	t	238	4
239	2019-01-08 14:12:10.769535+00	2019-01-08 14:12:10.769555+00	t	239	4
240	2019-01-08 14:12:10.801779+00	2019-01-08 14:12:10.801801+00	t	240	4
241	2019-01-08 14:12:10.837654+00	2019-01-08 14:12:10.83767+00	t	241	4
242	2019-01-08 14:12:10.872642+00	2019-01-08 14:12:10.872657+00	t	242	4
243	2019-01-08 14:12:10.906964+00	2019-01-08 14:12:10.906982+00	t	243	4
244	2019-01-08 14:12:10.939751+00	2019-01-08 14:12:10.939765+00	t	244	4
245	2019-01-08 14:12:10.974548+00	2019-01-08 14:12:10.974563+00	t	245	4
246	2019-01-08 14:12:11.010361+00	2019-01-08 14:12:11.01038+00	t	246	4
247	2019-01-08 14:12:11.044045+00	2019-01-08 14:12:11.044066+00	t	247	4
248	2019-01-08 14:12:11.079874+00	2019-01-08 14:12:11.079893+00	t	248	4
249	2019-01-08 14:12:11.113247+00	2019-01-08 14:12:11.113266+00	t	249	4
250	2019-01-08 14:12:11.145851+00	2019-01-08 14:12:11.145868+00	t	250	4
251	2019-01-08 14:12:11.178625+00	2019-01-08 14:12:11.178641+00	t	251	4
252	2019-01-08 14:12:11.210974+00	2019-01-08 14:12:11.210992+00	t	252	4
253	2019-01-08 14:12:11.24405+00	2019-01-08 14:12:11.244067+00	t	253	4
254	2019-01-08 14:12:11.280418+00	2019-01-08 14:12:11.280434+00	t	254	4
255	2019-01-08 14:12:11.318122+00	2019-01-08 14:12:11.31814+00	t	255	4
256	2019-01-08 14:12:11.351451+00	2019-01-08 14:12:11.351466+00	t	256	3
257	2019-01-08 14:12:11.384262+00	2019-01-08 14:12:11.384277+00	t	257	4
258	2019-01-08 14:12:11.417944+00	2019-01-08 14:12:11.417962+00	t	258	4
259	2019-01-08 14:12:11.449692+00	2019-01-08 14:12:11.449708+00	t	259	4
260	2019-01-08 14:12:11.48255+00	2019-01-08 14:12:11.482569+00	t	260	4
261	2019-01-08 14:12:11.516584+00	2019-01-08 14:12:11.516603+00	t	261	4
262	2019-01-08 14:12:11.548857+00	2019-01-08 14:12:11.548873+00	t	262	4
263	2019-01-08 14:12:11.580827+00	2019-01-08 14:12:11.580843+00	t	263	4
264	2019-01-08 14:12:11.612774+00	2019-01-08 14:12:11.612795+00	t	264	1
265	2019-01-08 14:12:11.646159+00	2019-01-08 14:12:11.646175+00	t	265	1
266	2019-01-08 14:12:11.678313+00	2019-01-08 14:12:11.67833+00	t	266	1
267	2019-01-08 14:12:11.709913+00	2019-01-08 14:12:11.709931+00	t	267	4
268	2019-01-08 14:12:11.742366+00	2019-01-08 14:12:11.742381+00	t	268	4
269	2019-01-08 14:12:11.774145+00	2019-01-08 14:12:11.774161+00	t	269	4
270	2019-01-09 04:45:22.617642+00	2019-01-09 04:45:22.617657+00	t	270	3
271	2019-01-09 04:45:22.654628+00	2019-01-09 04:45:22.654643+00	t	271	3
272	2019-01-09 04:45:22.690703+00	2019-01-09 04:45:22.690718+00	t	272	2
273	2019-01-09 04:45:22.721568+00	2019-01-09 04:45:22.721582+00	t	273	4
274	2019-01-09 04:45:22.760082+00	2019-01-09 04:45:22.760098+00	t	274	4
275	2019-01-09 04:45:22.792214+00	2019-01-09 04:45:22.792228+00	t	275	4
276	2019-01-09 04:45:22.826171+00	2019-01-09 04:45:22.826185+00	t	276	3
277	2019-01-09 04:45:22.860488+00	2019-01-09 04:45:22.860502+00	t	277	3
278	2019-01-09 04:45:22.893603+00	2019-01-09 04:45:22.893618+00	t	278	3
279	2019-01-09 04:45:22.9285+00	2019-01-09 04:45:22.928514+00	t	279	4
280	2019-01-09 04:45:22.958193+00	2019-01-09 04:45:22.958208+00	t	280	4
281	2019-01-09 04:45:22.993142+00	2019-01-09 04:45:22.993156+00	t	281	4
282	2019-01-09 04:45:23.028601+00	2019-01-09 04:45:23.028614+00	t	282	4
283	2019-01-09 04:45:23.058435+00	2019-01-09 04:45:23.058452+00	t	283	4
284	2019-01-09 04:45:23.093868+00	2019-01-09 04:45:23.093881+00	t	284	4
285	2019-01-09 04:45:23.129853+00	2019-01-09 04:45:23.129868+00	t	285	3
286	2019-01-09 04:45:23.160106+00	2019-01-09 04:45:23.160119+00	t	286	4
287	2019-01-09 04:45:23.196249+00	2019-01-09 04:45:23.196263+00	t	287	4
288	2019-01-09 04:45:23.228955+00	2019-01-09 04:45:23.22897+00	t	288	3
289	2019-01-09 04:45:23.263457+00	2019-01-09 04:45:23.263473+00	t	289	3
290	2019-01-09 04:45:23.295871+00	2019-01-09 04:45:23.295892+00	t	290	3
291	2019-01-09 04:45:23.327674+00	2019-01-09 04:45:23.327688+00	t	291	4
292	2019-01-09 04:45:23.360762+00	2019-01-09 04:45:23.360777+00	t	292	3
293	2019-01-09 04:45:23.396928+00	2019-01-09 04:45:23.396942+00	t	293	4
294	2019-01-09 04:45:23.427914+00	2019-01-09 04:45:23.427927+00	t	294	4
295	2019-01-09 04:45:23.459946+00	2019-01-09 04:45:23.459964+00	t	295	4
296	2019-01-09 04:45:23.493079+00	2019-01-09 04:45:23.493099+00	t	296	4
297	2019-01-09 04:45:23.527056+00	2019-01-09 04:45:23.527072+00	t	297	3
298	2019-01-09 04:45:23.558441+00	2019-01-09 04:45:23.558455+00	t	298	4
299	2019-01-09 04:45:23.591312+00	2019-01-09 04:45:23.591326+00	t	299	4
300	2019-01-09 04:45:23.622856+00	2019-01-09 04:45:23.622871+00	t	300	4
301	2019-01-09 04:45:23.65347+00	2019-01-09 04:45:23.653485+00	t	301	4
302	2019-01-09 04:45:23.68539+00	2019-01-09 04:45:23.685405+00	t	302	4
303	2019-01-09 04:45:23.715884+00	2019-01-09 04:45:23.715898+00	t	303	4
304	2019-01-09 04:45:23.746225+00	2019-01-09 04:45:23.74624+00	t	304	4
305	2019-01-09 04:45:23.777216+00	2019-01-09 04:45:23.77723+00	t	305	4
306	2019-01-09 04:45:23.808589+00	2019-01-09 04:45:23.808604+00	t	306	4
307	2019-01-09 04:45:23.841277+00	2019-01-09 04:45:23.841292+00	t	307	4
308	2019-01-09 04:45:23.872877+00	2019-01-09 04:45:23.87289+00	t	308	4
309	2019-01-09 04:45:23.904183+00	2019-01-09 04:45:23.904201+00	t	309	3
310	2019-01-09 04:45:23.937232+00	2019-01-09 04:45:23.937246+00	t	310	3
311	2019-01-09 04:45:23.971353+00	2019-01-09 04:45:23.971366+00	t	311	3
312	2019-01-09 04:45:24.006847+00	2019-01-09 04:45:24.006863+00	t	312	3
313	2019-01-09 04:45:24.041675+00	2019-01-09 04:45:24.041701+00	t	313	3
314	2019-01-09 04:45:24.075825+00	2019-01-09 04:45:24.07584+00	t	314	3
315	2019-01-09 04:45:24.111562+00	2019-01-09 04:45:24.111578+00	t	315	3
316	2019-01-09 04:45:24.142123+00	2019-01-09 04:45:24.142136+00	t	316	3
317	2019-01-09 04:45:24.174581+00	2019-01-09 04:45:24.174595+00	t	317	4
318	2019-01-09 04:45:24.208356+00	2019-01-09 04:45:24.208381+00	t	318	4
319	2019-01-09 04:45:24.241367+00	2019-01-09 04:45:24.241381+00	t	319	4
320	2019-01-09 04:45:24.272932+00	2019-01-09 04:45:24.272946+00	t	320	4
321	2019-01-09 04:45:24.309254+00	2019-01-09 04:45:24.309269+00	t	321	4
322	2019-01-09 04:45:24.340284+00	2019-01-09 04:45:24.340298+00	t	322	4
323	2019-01-09 04:45:24.378215+00	2019-01-09 04:45:24.378239+00	t	323	4
324	2019-01-09 04:45:24.409189+00	2019-01-09 04:45:24.409204+00	t	324	4
325	2019-01-09 04:45:24.441132+00	2019-01-09 04:45:24.441146+00	t	325	4
326	2019-01-09 04:45:24.47403+00	2019-01-09 04:45:24.474049+00	t	326	4
327	2019-01-09 04:45:24.50638+00	2019-01-09 04:45:24.506394+00	t	327	4
328	2019-01-09 04:45:24.537129+00	2019-01-09 04:45:24.537145+00	t	328	4
329	2019-01-09 04:45:24.569007+00	2019-01-09 04:45:24.569022+00	t	329	4
330	2019-01-09 04:45:24.600357+00	2019-01-09 04:45:24.600371+00	t	330	3
331	2019-01-09 04:45:24.630804+00	2019-01-09 04:45:24.63082+00	t	331	3
332	2019-01-09 04:45:24.661742+00	2019-01-09 04:45:24.661759+00	t	332	3
333	2019-01-09 04:45:24.692213+00	2019-01-09 04:45:24.692228+00	t	333	3
334	2019-01-09 04:45:24.725611+00	2019-01-09 04:45:24.72563+00	t	334	3
335	2019-01-09 04:45:24.759512+00	2019-01-09 04:45:24.759528+00	t	335	3
336	2019-01-09 04:45:24.791026+00	2019-01-09 04:45:24.791041+00	t	336	3
337	2019-01-09 04:45:24.826049+00	2019-01-09 04:45:24.826063+00	t	337	3
338	2019-01-09 04:45:24.873016+00	2019-01-09 04:45:24.873031+00	t	338	3
339	2019-01-09 04:45:24.904017+00	2019-01-09 04:45:24.904031+00	t	339	3
340	2019-01-09 04:45:24.945079+00	2019-01-09 04:45:24.945095+00	t	340	3
341	2019-01-09 04:45:24.982763+00	2019-01-09 04:45:24.982781+00	t	341	2
342	2019-01-09 04:45:25.049538+00	2019-01-09 04:45:25.049566+00	t	342	3
343	2019-01-09 04:45:25.086134+00	2019-01-09 04:45:25.086165+00	t	343	3
344	2019-01-09 04:45:25.121466+00	2019-01-09 04:45:25.121485+00	t	344	3
345	2019-01-09 04:45:25.159428+00	2019-01-09 04:45:25.15946+00	t	345	3
346	2019-01-09 04:45:25.191194+00	2019-01-09 04:45:25.19121+00	t	346	3
347	2019-01-09 04:45:25.224169+00	2019-01-09 04:45:25.224184+00	t	347	3
348	2019-01-09 04:45:25.255363+00	2019-01-09 04:45:25.255379+00	t	348	3
349	2019-01-09 04:45:25.289905+00	2019-01-09 04:45:25.28992+00	t	349	3
350	2019-01-09 04:45:25.321838+00	2019-01-09 04:45:25.321851+00	t	350	3
351	2019-01-09 04:45:25.355248+00	2019-01-09 04:45:25.355263+00	t	351	3
352	2019-01-09 04:45:25.389679+00	2019-01-09 04:45:25.389697+00	t	352	3
353	2019-01-09 04:45:25.432033+00	2019-01-09 04:45:25.432052+00	t	353	3
354	2019-01-09 04:45:25.466366+00	2019-01-09 04:45:25.466381+00	t	354	3
355	2019-01-09 04:45:25.499071+00	2019-01-09 04:45:25.499085+00	t	355	3
356	2019-01-09 04:45:25.535962+00	2019-01-09 04:45:25.535978+00	t	356	3
357	2019-01-09 04:45:25.567238+00	2019-01-09 04:45:25.567253+00	t	357	3
358	2019-01-09 04:45:25.600745+00	2019-01-09 04:45:25.60076+00	t	358	3
359	2019-01-09 04:45:25.635873+00	2019-01-09 04:45:25.635886+00	t	359	3
360	2019-01-09 04:45:25.669882+00	2019-01-09 04:45:25.669897+00	t	360	3
361	2019-01-09 04:45:25.701476+00	2019-01-09 04:45:25.701492+00	t	361	3
362	2019-01-09 04:45:25.734064+00	2019-01-09 04:45:25.734079+00	t	362	3
363	2019-01-09 04:45:25.765835+00	2019-01-09 04:45:25.765852+00	t	363	3
364	2019-01-09 04:45:25.797176+00	2019-01-09 04:45:25.797191+00	t	364	3
365	2019-01-09 04:45:25.828621+00	2019-01-09 04:45:25.828636+00	t	365	3
366	2019-01-09 04:45:25.862427+00	2019-01-09 04:45:25.862441+00	t	366	3
367	2019-01-09 04:45:25.893866+00	2019-01-09 04:45:25.893881+00	t	367	3
368	2019-01-09 04:45:25.924097+00	2019-01-09 04:45:25.924111+00	t	368	3
369	2019-01-09 04:45:25.95592+00	2019-01-09 04:45:25.955933+00	t	369	3
370	2019-01-09 04:45:25.989745+00	2019-01-09 04:45:25.98976+00	t	370	3
371	2019-01-09 04:45:26.047898+00	2019-01-09 04:45:26.047914+00	t	371	3
372	2019-01-09 04:45:26.078723+00	2019-01-09 04:45:26.078739+00	t	372	4
373	2019-01-09 04:45:26.121355+00	2019-01-09 04:45:26.121369+00	t	373	4
374	2019-01-09 04:45:26.152262+00	2019-01-09 04:45:26.152275+00	t	374	4
375	2019-01-09 04:45:26.182169+00	2019-01-09 04:45:26.182183+00	t	375	4
376	2019-01-09 04:45:26.212568+00	2019-01-09 04:45:26.212582+00	t	376	4
377	2019-01-09 04:45:26.243058+00	2019-01-09 04:45:26.243072+00	t	377	4
378	2019-01-09 04:45:26.274302+00	2019-01-09 04:45:26.274319+00	t	378	4
379	2019-01-09 04:45:26.305671+00	2019-01-09 04:45:26.305685+00	t	379	4
380	2019-01-09 04:45:26.337289+00	2019-01-09 04:45:26.337303+00	t	380	2
381	2019-01-09 09:44:04.349734+00	2019-01-09 09:44:04.349753+00	t	381	4
382	2019-01-09 09:44:04.383801+00	2019-01-09 09:44:04.383817+00	t	382	4
383	2019-01-09 09:44:04.416928+00	2019-01-09 09:44:04.416944+00	t	383	4
384	2019-01-09 09:44:04.450783+00	2019-01-09 09:44:04.450804+00	t	384	4
385	2019-01-09 09:44:04.484795+00	2019-01-09 09:44:04.484817+00	t	385	4
386	2019-01-09 09:44:04.519301+00	2019-01-09 09:44:04.519317+00	t	386	4
387	2019-01-09 09:44:04.551722+00	2019-01-09 09:44:04.551738+00	t	387	4
388	2019-01-09 09:44:04.584475+00	2019-01-09 09:44:04.584489+00	t	388	4
\.


--
-- Data for Name: products_productvendormapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_productvendormapping (id, product_price, created_at, modified_at, product_id, vendor_id) FROM stdin;
1	20	2019-01-08 12:07:51.218517+00	2019-01-08 12:07:51.218538+00	28	1
2	20	2019-01-08 12:07:51.218567+00	2019-01-08 12:07:51.218574+00	29	1
3	20	2019-01-08 12:07:51.218599+00	2019-01-08 12:07:51.218605+00	30	1
4	20	2019-01-08 12:07:51.218628+00	2019-01-08 12:07:51.218635+00	31	1
5	20	2019-01-08 12:07:51.218657+00	2019-01-08 12:07:51.218663+00	32	1
6	20	2019-01-08 12:07:51.218686+00	2019-01-08 12:07:51.218693+00	33	1
7	20	2019-01-08 12:07:51.218715+00	2019-01-08 12:07:51.218721+00	34	1
8	20	2019-01-08 12:07:51.218744+00	2019-01-08 12:07:51.21875+00	35	1
9	20	2019-01-08 12:07:51.218772+00	2019-01-08 12:07:51.218778+00	36	1
10	20	2019-01-08 12:07:51.218801+00	2019-01-08 12:07:51.218807+00	37	1
11	20	2019-01-08 12:07:51.21883+00	2019-01-08 12:07:51.218836+00	38	1
12	20	2019-01-08 12:07:51.218863+00	2019-01-08 12:07:51.21887+00	39	1
13	20	2019-01-08 12:07:51.218899+00	2019-01-08 12:07:51.218906+00	40	1
14	250	2019-01-09 07:48:36.851656+00	2019-01-09 07:48:36.851681+00	342	2
15	200	2019-01-09 07:48:36.853125+00	2019-01-09 07:48:36.853138+00	351	2
\.


--
-- Data for Name: products_size; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_size (id, size_value, size_unit, size_name, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: products_tax; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_tax (id, tax_name, tax_type, tax_percentage, tax_start_at, tax_end_at, created_at, modified_at, status) FROM stdin;
1	GST-0	gst	0	2019-01-01 00:30:00+00	\N	2019-01-08 05:20:55.576685+00	2019-01-08 05:20:55.576698+00	t
2	GST-5	gst	5	2019-01-01 00:30:00+00	\N	2019-01-08 05:21:17.369099+00	2019-01-08 05:21:17.369112+00	t
3	GST-12	gst	12	2019-01-01 00:30:00+00	\N	2019-01-08 05:21:38.661348+00	2019-01-08 05:21:38.661363+00	t
4	GST-18	gst	18	2019-01-01 00:30:00+00	\N	2019-01-08 05:21:59.690672+00	2019-01-08 05:21:59.690686+00	t
5	GST-28	gst	28	\N	\N	2019-01-09 10:54:35.414957+00	2019-01-09 10:54:35.414981+00	t
6	CESS - 12	cess	12	\N	\N	2019-01-09 10:54:52.860903+00	2019-01-09 10:54:52.860925+00	t
\.


--
-- Data for Name: products_weight; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.products_weight (id, weight_value, weight_unit, weight_name, created_at, modified_at, status) FROM stdin;
\.


--
-- Data for Name: retailer_to_gram_cart; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_cart (id, order_id, cart_status, created_at, modified_at, last_modified_by_id) FROM stdin;
7	ADT/07/70000	ordered	2019-01-09 06:29:41.915962+00	2019-01-09 06:44:35.830828+00	8
8	ADT/07/80000	ordered	2019-01-09 08:04:18.189331+00	2019-01-09 08:05:52.224245+00	10
6	ADT/07/60000	active	2019-01-09 06:18:50.993557+00	2019-01-09 09:25:03.90218+00	6
1	ADT/07/10000	ordered	2019-01-08 12:44:44.842433+00	2019-01-08 12:49:06.917772+00	6
2	ADT/07/20000	ordered	2019-01-08 12:51:05.421681+00	2019-01-08 12:51:41.904217+00	6
9	ADT/07/90000	ordered	2019-01-09 13:12:05.645057+00	2019-01-09 13:15:32.611014+00	13
3	ADT/07/30000	ordered	2019-01-08 12:52:14.745185+00	2019-01-08 13:19:10.474124+00	6
4	ADT/07/40000	ordered	2019-01-08 14:00:02.237274+00	2019-01-08 14:00:15.435672+00	6
5	ADT/07/50000	ordered	2019-01-09 06:04:35.400381+00	2019-01-09 06:05:28.007204+00	6
10	ADT/07/10000	active	2019-01-09 13:16:30.772414+00	2019-01-09 13:19:48.365279+00	13
\.


--
-- Data for Name: retailer_to_gram_cartproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_cartproductmapping (id, qty, qty_error_msg, created_at, modified_at, cart_id, cart_product_id) FROM stdin;
30	1		2019-01-09 13:12:09.34203+00	2019-01-09 13:14:48.649583+00	9	29
6	1		2019-01-08 12:48:17.632267+00	2019-01-08 12:48:21.858013+00	1	31
5	1		2019-01-08 12:48:16.354468+00	2019-01-08 12:48:22.030884+00	1	29
4	1		2019-01-08 12:48:14.677696+00	2019-01-08 12:48:22.184894+00	1	28
9	1		2019-01-08 12:51:13.399441+00	2019-01-08 12:51:24.660119+00	2	31
8	1		2019-01-08 12:51:11.121918+00	2019-01-08 12:51:24.824437+00	2	29
7	1		2019-01-08 12:51:05.433627+00	2019-01-08 12:51:25.027804+00	2	28
13	1		2019-01-08 13:18:42.863117+00	2019-01-08 13:18:48.324858+00	3	31
12	1		2019-01-08 13:18:41.077839+00	2019-01-08 13:18:48.489017+00	3	29
11	1		2019-01-08 13:18:39.061402+00	2019-01-08 13:18:48.648866+00	3	28
16	1		2019-01-08 14:00:05.784466+00	2019-01-08 14:00:08.847708+00	4	31
15	1		2019-01-08 14:00:04.400906+00	2019-01-08 14:00:09.118557+00	4	29
14	1		2019-01-08 14:00:02.267226+00	2019-01-08 14:00:09.284439+00	4	28
17	1		2019-01-09 06:04:35.41239+00	2019-01-09 06:04:58.165965+00	5	31
18	1		2019-01-09 06:04:37.723843+00	2019-01-09 06:04:58.337857+00	5	29
19	1		2019-01-09 06:04:39.381392+00	2019-01-09 06:04:58.621298+00	5	28
25	5		2019-01-09 06:29:45.675153+00	2019-01-09 06:41:30.264369+00	7	28
24	2		2019-01-09 06:29:43.976961+00	2019-01-09 06:41:30.457147+00	7	29
23	4		2019-01-09 06:29:41.925685+00	2019-01-09 06:41:30.640424+00	7	31
36	13	Available Quantity : 0	2019-01-09 13:19:16.959173+00	2019-01-09 13:19:51.598787+00	10	29
37	1	Available Quantity : 0	2019-01-09 13:19:48.371765+00	2019-01-09 13:19:51.699473+00	10	31
26	1		2019-01-09 08:04:18.203448+00	2019-01-09 08:04:38.707719+00	8	28
27	1		2019-01-09 08:04:23.907786+00	2019-01-09 08:04:38.867528+00	8	29
22	1		2019-01-09 06:20:59.40466+00	2019-01-09 09:25:05.90572+00	6	31
21	1		2019-01-09 06:19:09.14316+00	2019-01-09 09:25:06.177227+00	6	29
28	1	Available Quantity : 0	2019-01-09 09:23:34.879853+00	2019-01-09 09:25:06.362604+00	6	28
\.


--
-- Data for Name: retailer_to_gram_customercare; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_customercare (id, name, email_us, contact_us, created_at, modified_at, order_status, select_issue, complaint_detail, order_id_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_gram_note; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_note (id, note_type, amount, created_at, modified_at, last_modified_by_id, order_id, ordered_product_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_gram_order; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_order (id, order_no, total_mrp, total_discount_amount, total_tax_amount, total_final_amount, order_status, payment_mode, reference_no, payment_amount, payment_status, created_at, modified_at, billing_address_id, buyer_shop_id, last_modified_by_id, ordered_by_id, ordered_cart_id, received_by_id, seller_shop_id, shipping_address_id) FROM stdin;
1	ADT/07/10000	680.92999999999995	0	0	680.92999999999995	payment_done_approval_pending		\N	0	\N	2019-01-08 12:49:06.932499+00	2019-01-08 12:49:07.661757+00	5	3	6	6	1	\N	1	4
2	ADT/07/20000	680.92999999999995	0	0	680.92999999999995	payment_done_approval_pending		\N	0	\N	2019-01-08 12:51:41.913428+00	2019-01-08 12:51:42.475631+00	5	3	6	6	2	\N	1	4
3	ADT/07/30000	680.92999999999995	0	0	680.92999999999995	payment_done_approval_pending		\N	0	\N	2019-01-08 13:19:10.485079+00	2019-01-08 13:19:11.157989+00	5	3	6	6	3	\N	1	4
4	ADT/07/40000	680.92999999999995	0	0	680.92999999999995	payment_done_approval_pending		\N	0	\N	2019-01-08 14:00:15.444693+00	2019-01-08 14:00:16.166949+00	5	3	6	6	4	\N	1	4
5	ADT/07/50000	680.92999999999995	0	0	680.92999999999995	payment_done_approval_pending		\N	0	\N	2019-01-09 06:05:28.016758+00	2019-01-09 06:05:29.029355+00	5	3	6	6	5	\N	1	4
6	ADT/07/70000	2629.96000000000004	0	0	2629.96000000000004	payment_done_approval_pending		\N	0	\N	2019-01-09 06:44:35.840909+00	2019-01-09 06:44:36.493196+00	7	4	8	8	7	\N	1	6
7	ADT/07/80000	471.800000000000011	0	0	471.800000000000011	payment_done_approval_pending		\N	0	\N	2019-01-09 08:05:52.23426+00	2019-01-09 08:05:52.791257+00	10	6	10	10	8	\N	1	9
8	ADT/07/90000	188.52000000000001	0	0	188.52000000000001	payment_done_approval_pending		\N	0	\N	2019-01-09 13:15:32.620928+00	2019-01-09 13:15:33.18713+00	14	8	13	13	9	\N	1	13
\.


--
-- Data for Name: retailer_to_gram_orderedproduct; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_orderedproduct (id, invoice_no, vehicle_no, created_at, modified_at, last_modified_by_id, order_id, received_by_id, shipped_by_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_gram_orderedproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_orderedproductmapping (id, shipped_qty, delivered_qty, returned_qty, damaged_qty, created_at, modified_at, last_modified_by_id, ordered_product_id, product_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_gram_payment; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_gram_payment (id, name, paid_amount, payment_choice, neft_reference_number, payment_status, order_id_id) FROM stdin;
1	Payment/1	680.9300	cash_on_delivery		payment_done_approval_pending	1
2	Payment/2	680.9300	neft	66u865	payment_done_approval_pending	2
3	Payment/3	680.9300	cash_on_delivery		payment_done_approval_pending	3
4	Payment/4	680.9300	neft	26w6w6	payment_done_approval_pending	4
5	Payment/5	680.9300	cash_on_delivery		payment_done_approval_pending	5
6	Payment/6	2629.9600	cash_on_delivery		payment_done_approval_pending	6
7	Payment/7	471.8000	neft	677	payment_done_approval_pending	7
8	Payment/8	188.5200	cash_on_delivery		payment_done_approval_pending	8
\.


--
-- Data for Name: retailer_to_sp_cart; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_cart (id, order_id, cart_status, created_at, modified_at, last_modified_by_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_cartproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_cartproductmapping (id, qty, qty_error_msg, created_at, modified_at, cart_id, cart_product_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_customercare; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_customercare (id, name, email_us, contact_us, created_at, modified_at, order_status, select_issue, complaint_detail, order_id_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_note; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_note (id, note_type, amount, created_at, modified_at, last_modified_by_id, order_id, ordered_product_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_order; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_order (id, order_no, total_mrp, total_discount_amount, total_tax_amount, total_final_amount, order_status, payment_mode, reference_no, payment_amount, payment_status, created_at, modified_at, billing_address_id, buyer_shop_id, last_modified_by_id, ordered_by_id, ordered_cart_id, received_by_id, seller_shop_id, shipping_address_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_orderedproduct; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_orderedproduct (id, invoice_no, vehicle_no, created_at, modified_at, last_modified_by_id, order_id, received_by_id, shipped_by_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_orderedproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_orderedproductmapping (id, shipped_qty, delivered_qty, returned_qty, damaged_qty, created_at, modified_at, last_modified_by_id, ordered_product_id, product_id) FROM stdin;
\.


--
-- Data for Name: retailer_to_sp_payment; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.retailer_to_sp_payment (id, name, paid_amount, payment_choice, neft_reference_number, payment_status, order_id_id) FROM stdin;
\.


--
-- Data for Name: shops_parentretailermapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_parentretailermapping (id, created_at, modified_at, status, parent_id, retailer_id) FROM stdin;
1	2019-01-08 12:42:01.109512+00	2019-01-08 12:42:01.10954+00	t	1	3
2	2019-01-09 06:27:35.215507+00	2019-01-09 06:27:35.215538+00	t	1	4
3	2019-01-09 07:16:31.403591+00	2019-01-09 07:16:31.403619+00	t	1	5
4	2019-01-09 08:03:42.144731+00	2019-01-09 08:03:42.144755+00	t	1	6
5	2019-01-09 13:11:32.590478+00	2019-01-09 13:11:32.590508+00	t	1	8
\.


--
-- Data for Name: shops_retailertype; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_retailertype (id, retailer_type_name, created_at, modified_at, status) FROM stdin;
1	gm	2019-01-08 11:44:44.780803+00	2019-01-08 12:40:59.259254+00	t
\.


--
-- Data for Name: shops_shop; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_shop (id, shop_name, created_at, modified_at, status, shop_owner_id, shop_type_id) FROM stdin;
3	baniya general store	2019-01-08 12:37:17.95643+00	2019-01-08 12:39:42.826848+00	t	6	1
1	Gramfactory-Noida	2019-01-08 11:45:32.201872+00	2019-01-08 12:41:23.72991+00	t	2	2
4	Arzoo Apartment Shop	2019-01-09 06:22:22.909271+00	2019-01-09 06:27:22.534656+00	t	8	1
5	Pal Shop	2019-01-09 07:10:53.61259+00	2019-01-09 07:16:07.713048+00	t	9	1
6	Nikita ki shop	2019-01-09 08:01:20.201631+00	2019-01-09 08:03:42.075247+00	t	10	1
7	GFDN-Noida	2019-01-09 10:59:36.471273+00	2019-01-09 10:59:36.471303+00	t	12	2
8	store 3	2019-01-09 11:55:32.444615+00	2019-01-09 13:11:30.275249+00	t	13	1
\.


--
-- Data for Name: shops_shop_related_users; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_shop_related_users (id, shop_id, user_id) FROM stdin;
\.


--
-- Data for Name: shops_shopdocument; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_shopdocument (id, shop_document_type, shop_document_number, shop_document_photo, shop_name_id) FROM stdin;
2	sln	tttgghiiiyyyyuuuu	shop_photos/shop_name/documents/IMG_20190108_180854.jpg	3
3	sln	555562359856	shop_photos/shop_name/documents/IMG-20190109-WA0000.jpg	4
4	sln	I	shop_photos/shop_name/documents/IMG_20190109_124300.jpg	5
5	sln	67902	shop_photos/shop_name/documents/Screenshot_20181225-065104_Google.jpg	6
6	gstin	09AAQCA9570J1ZW	shop_photos/shop_name/documents/NOIDA_AEOP_1.pdf	7
7	uidai	784839293939	shop_photos/shop_name/documents/IMG_20181130_143931.jpg	8
\.


--
-- Data for Name: shops_shopphoto; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_shopphoto (id, shop_photo, shop_name_id) FROM stdin;
2	shop_photos/shop_name/IMG_20190108_180822.jpg	3
3	shop_photos/shop_name/IMG-20190109-WA0000.jpg	4
4	shop_photos/shop_name/IMG_20190109_124238.jpg	5
5	shop_photos/shop_name/IMG-20190108-WA0066.jpg	6
6	shop_photos/shop_name/IMG_20181130_171835.jpg	8
\.


--
-- Data for Name: shops_shoptype; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.shops_shoptype (id, shop_type, created_at, modified_at, status, shop_sub_type_id) FROM stdin;
1	r	2019-01-08 11:44:46.890225+00	2019-01-08 12:41:01.232231+00	t	1
2	gf	2019-01-08 12:41:11.309347+00	2019-01-08 12:41:11.309376+00	t	1
\.


--
-- Data for Name: sp_to_gram_cart; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_cart (id, po_no, po_status, po_creation_date, po_validity_date, payment_term, delivery_term, po_amount, created_at, modified_at, last_modified_by_id, po_raised_by_id, shop_id) FROM stdin;
\.


--
-- Data for Name: sp_to_gram_cartproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_cartproductmapping (id, case_size, number_of_cases, qty, scheme, price, total_price, cart_id, cart_product_id) FROM stdin;
\.


--
-- Data for Name: sp_to_gram_order; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_order (id, order_no, total_mrp, total_discount_amount, total_tax_amount, total_final_amount, order_status, created_at, modified_at, billing_address_id, last_modified_by_id, ordered_by_id, ordered_cart_id, received_by_id, shipping_address_id) FROM stdin;
\.


--
-- Data for Name: sp_to_gram_orderedproduct; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_orderedproduct (id, invoice_no, vehicle_no, created_at, modified_at, last_modified_by_id, order_id, received_by_id, shipped_by_id) FROM stdin;
\.


--
-- Data for Name: sp_to_gram_orderedproductmapping; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_orderedproductmapping (id, manufacture_date, expiry_date, shipped_qty, available_qty, ordered_qty, delivered_qty, returned_qty, damaged_qty, created_at, modified_at, last_modified_by_id, ordered_product_id, product_id) FROM stdin;
\.


--
-- Data for Name: sp_to_gram_orderedproductreserved; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_orderedproductreserved (id, reserved_qty, order_reserve_end_time, created_at, modified_at, cart_id, order_product_reserved_id, product_id, reserve_status) FROM stdin;
\.


--
-- Data for Name: sp_to_gram_spnote; Type: TABLE DATA; Schema: public; Owner: gramfac18
--

COPY public.sp_to_gram_spnote (id, brand_note_id, note_type, amount, created_at, modified_at, grn_order_id, last_modified_by_id, order_id) FROM stdin;
\.


--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.account_emailaddress_id_seq', 5, true);


--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.account_emailconfirmation_id_seq', 1, false);


--
-- Name: accounts_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.accounts_user_groups_id_seq', 1, false);


--
-- Name: accounts_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.accounts_user_id_seq', 13, true);


--
-- Name: accounts_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.accounts_user_user_permissions_id_seq', 379, true);


--
-- Name: accounts_userdocument_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.accounts_userdocument_id_seq', 1, false);


--
-- Name: addresses_address_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.addresses_address_id_seq', 14, true);


--
-- Name: addresses_area_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.addresses_area_id_seq', 1, false);


--
-- Name: addresses_city_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.addresses_city_id_seq', 5, true);


--
-- Name: addresses_country_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.addresses_country_id_seq', 1, true);


--
-- Name: addresses_invoicecitymapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.addresses_invoicecitymapping_id_seq', 1, false);


--
-- Name: addresses_state_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.addresses_state_id_seq', 3, true);


--
-- Name: allauth_socialaccount_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.allauth_socialaccount_id_seq', 1, false);


--
-- Name: allauth_socialapp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.allauth_socialapp_id_seq', 1, false);


--
-- Name: allauth_socialapp_sites_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.allauth_socialapp_sites_id_seq', 1, false);


--
-- Name: allauth_socialtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.allauth_socialtoken_id_seq', 1, false);


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 379, true);


--
-- Name: banner_banner_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.banner_banner_id_seq', 6, true);


--
-- Name: banner_bannerdata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.banner_bannerdata_id_seq', 6, true);


--
-- Name: banner_bannerposition_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.banner_bannerposition_id_seq', 1, true);


--
-- Name: banner_bannerslot_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.banner_bannerslot_id_seq', 1, true);


--
-- Name: banner_page_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.banner_page_id_seq', 1, true);


--
-- Name: brand_brand_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.brand_brand_id_seq', 119, true);


--
-- Name: brand_branddata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.brand_branddata_id_seq', 36, true);


--
-- Name: brand_brandposition_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.brand_brandposition_id_seq', 1, true);


--
-- Name: brand_vendor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.brand_vendor_id_seq', 2, true);


--
-- Name: categories_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.categories_category_id_seq', 43, true);


--
-- Name: categories_categorydata_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.categories_categorydata_id_seq', 13, true);


--
-- Name: categories_categoryposation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.categories_categoryposation_id_seq', 1, true);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 336, true);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 94, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 40, true);


--
-- Name: django_site_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.django_site_id_seq', 1, true);


--
-- Name: gram_to_brand_brandnote_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_brandnote_id_seq', 1, false);


--
-- Name: gram_to_brand_cart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_cart_id_seq', 2, true);


--
-- Name: gram_to_brand_cartproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_cartproductmapping_id_seq', 5, true);


--
-- Name: gram_to_brand_grnorder_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_grnorder_id_seq', 4, true);


--
-- Name: gram_to_brand_grnorderproducthistory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_grnorderproducthistory_id_seq', 1, false);


--
-- Name: gram_to_brand_grnorderproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_grnorderproductmapping_id_seq', 12, true);


--
-- Name: gram_to_brand_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_order_id_seq', 2, true);


--
-- Name: gram_to_brand_orderedproductreserved_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_orderedproductreserved_id_seq', 111, true);


--
-- Name: gram_to_brand_orderhistory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_orderhistory_id_seq', 1, false);


--
-- Name: gram_to_brand_orderitem_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_orderitem_id_seq', 5, true);


--
-- Name: gram_to_brand_picklist_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_picklist_id_seq', 10, true);


--
-- Name: gram_to_brand_picklistitems_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_picklistitems_id_seq', 111, true);


--
-- Name: gram_to_brand_po_message_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.gram_to_brand_po_message_id_seq', 1, false);


--
-- Name: otp_phoneotp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.otp_phoneotp_id_seq', 12, true);


--
-- Name: products_color_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_color_id_seq', 1, false);


--
-- Name: products_flavor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_flavor_id_seq', 1, false);


--
-- Name: products_fragrance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_fragrance_id_seq', 1, false);


--
-- Name: products_packagesize_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_packagesize_id_seq', 1, false);


--
-- Name: products_product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_product_id_seq', 389, true);


--
-- Name: products_productcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productcategory_id_seq', 390, true);


--
-- Name: products_productcategoryhistory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productcategoryhistory_id_seq', 1, false);


--
-- Name: products_productcsv_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productcsv_id_seq', 1, false);


--
-- Name: products_producthistory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_producthistory_id_seq', 1, false);


--
-- Name: products_productimage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productimage_id_seq', 2, true);


--
-- Name: products_productoption_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productoption_id_seq', 389, true);


--
-- Name: products_productprice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productprice_id_seq', 13, true);


--
-- Name: products_productpricecsv_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productpricecsv_id_seq', 1, false);


--
-- Name: products_productskugenerator_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productskugenerator_id_seq', 390, true);


--
-- Name: products_producttaxmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_producttaxmapping_id_seq', 390, true);


--
-- Name: products_productvendormapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_productvendormapping_id_seq', 15, true);


--
-- Name: products_size_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_size_id_seq', 1, false);


--
-- Name: products_tax_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_tax_id_seq', 6, true);


--
-- Name: products_weight_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.products_weight_id_seq', 1, false);


--
-- Name: retailer_to_gram_cart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_cart_id_seq', 10, true);


--
-- Name: retailer_to_gram_cartproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_cartproductmapping_id_seq', 37, true);


--
-- Name: retailer_to_gram_customercare_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_customercare_id_seq', 1, false);


--
-- Name: retailer_to_gram_note_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_note_id_seq', 1, false);


--
-- Name: retailer_to_gram_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_order_id_seq', 8, true);


--
-- Name: retailer_to_gram_orderedproduct_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_orderedproduct_id_seq', 1, false);


--
-- Name: retailer_to_gram_orderedproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_orderedproductmapping_id_seq', 1, false);


--
-- Name: retailer_to_gram_payment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_gram_payment_id_seq', 8, true);


--
-- Name: retailer_to_sp_cart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_cart_id_seq', 1, false);


--
-- Name: retailer_to_sp_cartproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_cartproductmapping_id_seq', 1, false);


--
-- Name: retailer_to_sp_customercare_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_customercare_id_seq', 1, false);


--
-- Name: retailer_to_sp_note_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_note_id_seq', 1, false);


--
-- Name: retailer_to_sp_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_order_id_seq', 1, false);


--
-- Name: retailer_to_sp_orderedproduct_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_orderedproduct_id_seq', 1, false);


--
-- Name: retailer_to_sp_orderedproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_orderedproductmapping_id_seq', 1, false);


--
-- Name: retailer_to_sp_payment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.retailer_to_sp_payment_id_seq', 1, false);


--
-- Name: shops_parentretailermapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_parentretailermapping_id_seq', 5, true);


--
-- Name: shops_retailertype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_retailertype_id_seq', 1, true);


--
-- Name: shops_shop_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_shop_id_seq', 9, true);


--
-- Name: shops_shop_related_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_shop_related_users_id_seq', 1, false);


--
-- Name: shops_shopdocument_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_shopdocument_id_seq', 7, true);


--
-- Name: shops_shopphoto_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_shopphoto_id_seq', 6, true);


--
-- Name: shops_shoptype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.shops_shoptype_id_seq', 2, true);


--
-- Name: sp_to_gram_cart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_cart_id_seq', 1, false);


--
-- Name: sp_to_gram_cartproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_cartproductmapping_id_seq', 1, false);


--
-- Name: sp_to_gram_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_order_id_seq', 1, false);


--
-- Name: sp_to_gram_orderedproduct_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_orderedproduct_id_seq', 1, false);


--
-- Name: sp_to_gram_orderedproductmapping_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_orderedproductmapping_id_seq', 1, false);


--
-- Name: sp_to_gram_orderedproductreserved_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_orderedproductreserved_id_seq', 1, false);


--
-- Name: sp_to_gram_spnote_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gramfac18
--

SELECT pg_catalog.setval('public.sp_to_gram_spnote_id_seq', 1, false);


--
-- Name: account_emailaddress account_emailaddress_email_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailaddress
    ADD CONSTRAINT account_emailaddress_email_key UNIQUE (email);


--
-- Name: account_emailaddress account_emailaddress_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailaddress
    ADD CONSTRAINT account_emailaddress_pkey PRIMARY KEY (id);


--
-- Name: account_emailconfirmation account_emailconfirmation_key_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailconfirmation
    ADD CONSTRAINT account_emailconfirmation_key_key UNIQUE (key);


--
-- Name: account_emailconfirmation account_emailconfirmation_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailconfirmation
    ADD CONSTRAINT account_emailconfirmation_pkey PRIMARY KEY (id);


--
-- Name: accounts_user_groups accounts_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_pkey PRIMARY KEY (id);


--
-- Name: accounts_user_groups accounts_user_groups_user_id_group_id_59c0b32f_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_user_id_group_id_59c0b32f_uniq UNIQUE (user_id, group_id);


--
-- Name: accounts_user accounts_user_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user
    ADD CONSTRAINT accounts_user_phone_number_key UNIQUE (phone_number);


--
-- Name: accounts_user accounts_user_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user
    ADD CONSTRAINT accounts_user_pkey PRIMARY KEY (id);


--
-- Name: accounts_user_user_permissions accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq UNIQUE (user_id, permission_id);


--
-- Name: accounts_user_user_permissions accounts_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: accounts_userdocument accounts_userdocument_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_userdocument
    ADD CONSTRAINT accounts_userdocument_pkey PRIMARY KEY (id);


--
-- Name: addresses_address addresses_address_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_address
    ADD CONSTRAINT addresses_address_pkey PRIMARY KEY (id);


--
-- Name: addresses_area addresses_area_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_area
    ADD CONSTRAINT addresses_area_pkey PRIMARY KEY (id);


--
-- Name: addresses_city addresses_city_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_city
    ADD CONSTRAINT addresses_city_pkey PRIMARY KEY (id);


--
-- Name: addresses_country addresses_country_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_country
    ADD CONSTRAINT addresses_country_pkey PRIMARY KEY (id);


--
-- Name: addresses_invoicecitymapping addresses_invoicecitymapping_city_id_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_invoicecitymapping
    ADD CONSTRAINT addresses_invoicecitymapping_city_id_key UNIQUE (city_id);


--
-- Name: addresses_invoicecitymapping addresses_invoicecitymapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_invoicecitymapping
    ADD CONSTRAINT addresses_invoicecitymapping_pkey PRIMARY KEY (id);


--
-- Name: addresses_state addresses_state_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_state
    ADD CONSTRAINT addresses_state_pkey PRIMARY KEY (id);


--
-- Name: allauth_socialaccount allauth_socialaccount_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialaccount
    ADD CONSTRAINT allauth_socialaccount_pkey PRIMARY KEY (id);


--
-- Name: allauth_socialaccount allauth_socialaccount_provider_uid_519b3f87_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialaccount
    ADD CONSTRAINT allauth_socialaccount_provider_uid_519b3f87_uniq UNIQUE (provider, uid);


--
-- Name: allauth_socialapp allauth_socialapp_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp
    ADD CONSTRAINT allauth_socialapp_pkey PRIMARY KEY (id);


--
-- Name: allauth_socialapp_sites allauth_socialapp_sites_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp_sites
    ADD CONSTRAINT allauth_socialapp_sites_pkey PRIMARY KEY (id);


--
-- Name: allauth_socialapp_sites allauth_socialapp_sites_socialapp_id_site_id_d73b0d46_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp_sites
    ADD CONSTRAINT allauth_socialapp_sites_socialapp_id_site_id_d73b0d46_uniq UNIQUE (socialapp_id, site_id);


--
-- Name: allauth_socialtoken allauth_socialtoken_app_id_account_id_e92f2582_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialtoken
    ADD CONSTRAINT allauth_socialtoken_app_id_account_id_e92f2582_uniq UNIQUE (app_id, account_id);


--
-- Name: allauth_socialtoken allauth_socialtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialtoken
    ADD CONSTRAINT allauth_socialtoken_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: authtoken_token authtoken_token_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_pkey PRIMARY KEY (key);


--
-- Name: authtoken_token authtoken_token_user_id_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_key UNIQUE (user_id);


--
-- Name: banner_banner banner_banner_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_banner
    ADD CONSTRAINT banner_banner_pkey PRIMARY KEY (id);


--
-- Name: banner_bannerdata banner_bannerdata_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerdata
    ADD CONSTRAINT banner_bannerdata_pkey PRIMARY KEY (id);


--
-- Name: banner_bannerposition banner_bannerposition_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerposition
    ADD CONSTRAINT banner_bannerposition_pkey PRIMARY KEY (id);


--
-- Name: banner_bannerslot banner_bannerslot_name_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerslot
    ADD CONSTRAINT banner_bannerslot_name_key UNIQUE (name);


--
-- Name: banner_bannerslot banner_bannerslot_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerslot
    ADD CONSTRAINT banner_bannerslot_pkey PRIMARY KEY (id);


--
-- Name: banner_page banner_page_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_page
    ADD CONSTRAINT banner_page_pkey PRIMARY KEY (id);


--
-- Name: brand_brand brand_brand_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_brand
    ADD CONSTRAINT brand_brand_pkey PRIMARY KEY (id);


--
-- Name: brand_branddata brand_branddata_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_branddata
    ADD CONSTRAINT brand_branddata_pkey PRIMARY KEY (id);


--
-- Name: brand_brandposition brand_brandposition_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_brandposition
    ADD CONSTRAINT brand_brandposition_pkey PRIMARY KEY (id);


--
-- Name: brand_vendor brand_vendor_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_vendor
    ADD CONSTRAINT brand_vendor_pkey PRIMARY KEY (id);


--
-- Name: categories_category categories_category_category_name_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category
    ADD CONSTRAINT categories_category_category_name_key UNIQUE (category_name);


--
-- Name: categories_category categories_category_category_sku_part_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category
    ADD CONSTRAINT categories_category_category_sku_part_key UNIQUE (category_sku_part);


--
-- Name: categories_category categories_category_category_slug_category_p_0a44144b_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category
    ADD CONSTRAINT categories_category_category_slug_category_p_0a44144b_uniq UNIQUE (category_slug, category_parent_id);


--
-- Name: categories_category categories_category_category_slug_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category
    ADD CONSTRAINT categories_category_category_slug_key UNIQUE (category_slug);


--
-- Name: categories_category categories_category_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category
    ADD CONSTRAINT categories_category_pkey PRIMARY KEY (id);


--
-- Name: categories_categorydata categories_categorydata_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_categorydata
    ADD CONSTRAINT categories_categorydata_pkey PRIMARY KEY (id);


--
-- Name: categories_categoryposation categories_categoryposation_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_categoryposation
    ADD CONSTRAINT categories_categoryposation_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: django_site django_site_domain_a2e37b91_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_site
    ADD CONSTRAINT django_site_domain_a2e37b91_uniq UNIQUE (domain);


--
-- Name: django_site django_site_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_site
    ADD CONSTRAINT django_site_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_brandnote gram_to_brand_brandnote_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_brandnote
    ADD CONSTRAINT gram_to_brand_brandnote_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_cart gram_to_brand_cart_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_cartproductmapping gram_to_brand_cartproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cartproductmapping
    ADD CONSTRAINT gram_to_brand_cartproductmapping_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_grnorder gram_to_brand_grnorder_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorder
    ADD CONSTRAINT gram_to_brand_grnorder_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_grnorderproducthistory gram_to_brand_grnorderproducthistory_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory
    ADD CONSTRAINT gram_to_brand_grnorderproducthistory_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_grnorderproductmapping gram_to_brand_grnorderproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproductmapping
    ADD CONSTRAINT gram_to_brand_grnorderproductmapping_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_order gram_to_brand_order_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_orderedproductreserved gram_to_brand_orderedproductreserved_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderedproductreserved
    ADD CONSTRAINT gram_to_brand_orderedproductreserved_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderhistory_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderhistory_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_orderitem gram_to_brand_orderitem_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderitem
    ADD CONSTRAINT gram_to_brand_orderitem_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_picklist gram_to_brand_picklist_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklist
    ADD CONSTRAINT gram_to_brand_picklist_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_picklistitems gram_to_brand_picklistitems_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklistitems
    ADD CONSTRAINT gram_to_brand_picklistitems_pkey PRIMARY KEY (id);


--
-- Name: gram_to_brand_po_message gram_to_brand_po_message_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_po_message
    ADD CONSTRAINT gram_to_brand_po_message_pkey PRIMARY KEY (id);


--
-- Name: otp_phoneotp otp_phoneotp_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.otp_phoneotp
    ADD CONSTRAINT otp_phoneotp_pkey PRIMARY KEY (id);


--
-- Name: products_color products_color_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_color
    ADD CONSTRAINT products_color_pkey PRIMARY KEY (id);


--
-- Name: products_flavor products_flavor_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_flavor
    ADD CONSTRAINT products_flavor_pkey PRIMARY KEY (id);


--
-- Name: products_fragrance products_fragrance_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_fragrance
    ADD CONSTRAINT products_fragrance_pkey PRIMARY KEY (id);


--
-- Name: products_packagesize products_packagesize_pack_size_name_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_packagesize
    ADD CONSTRAINT products_packagesize_pack_size_name_key UNIQUE (pack_size_name);


--
-- Name: products_packagesize products_packagesize_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_packagesize
    ADD CONSTRAINT products_packagesize_pkey PRIMARY KEY (id);


--
-- Name: products_product products_product_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_product
    ADD CONSTRAINT products_product_pkey PRIMARY KEY (id);


--
-- Name: products_product products_product_product_gf_code_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_product
    ADD CONSTRAINT products_product_product_gf_code_key UNIQUE (product_gf_code);


--
-- Name: products_product products_product_product_sku_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_product
    ADD CONSTRAINT products_product_product_sku_key UNIQUE (product_sku);


--
-- Name: products_productcategory products_productcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategory
    ADD CONSTRAINT products_productcategory_pkey PRIMARY KEY (id);


--
-- Name: products_productcategoryhistory products_productcategoryhistory_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategoryhistory
    ADD CONSTRAINT products_productcategoryhistory_pkey PRIMARY KEY (id);


--
-- Name: products_productcsv products_productcsv_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcsv
    ADD CONSTRAINT products_productcsv_pkey PRIMARY KEY (id);


--
-- Name: products_producthistory products_producthistory_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_producthistory
    ADD CONSTRAINT products_producthistory_pkey PRIMARY KEY (id);


--
-- Name: products_productimage products_productimage_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productimage
    ADD CONSTRAINT products_productimage_pkey PRIMARY KEY (id);


--
-- Name: products_productoption products_productoption_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productoption_pkey PRIMARY KEY (id);


--
-- Name: products_productprice products_productprice_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productprice
    ADD CONSTRAINT products_productprice_pkey PRIMARY KEY (id);


--
-- Name: products_productpricecsv products_productpricecsv_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productpricecsv
    ADD CONSTRAINT products_productpricecsv_pkey PRIMARY KEY (id);


--
-- Name: products_productskugenerator products_productskugenerator_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productskugenerator
    ADD CONSTRAINT products_productskugenerator_pkey PRIMARY KEY (id);


--
-- Name: products_producttaxmapping products_producttaxmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_producttaxmapping
    ADD CONSTRAINT products_producttaxmapping_pkey PRIMARY KEY (id);


--
-- Name: products_productvendormapping products_productvendormapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productvendormapping
    ADD CONSTRAINT products_productvendormapping_pkey PRIMARY KEY (id);


--
-- Name: products_size products_size_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_size
    ADD CONSTRAINT products_size_pkey PRIMARY KEY (id);


--
-- Name: products_size products_size_size_name_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_size
    ADD CONSTRAINT products_size_size_name_key UNIQUE (size_name);


--
-- Name: products_tax products_tax_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_tax
    ADD CONSTRAINT products_tax_pkey PRIMARY KEY (id);


--
-- Name: products_weight products_weight_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_weight
    ADD CONSTRAINT products_weight_pkey PRIMARY KEY (id);


--
-- Name: products_weight products_weight_weight_name_key; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_weight
    ADD CONSTRAINT products_weight_weight_name_key UNIQUE (weight_name);


--
-- Name: retailer_to_gram_cart retailer_to_gram_cart_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cart
    ADD CONSTRAINT retailer_to_gram_cart_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_cartproductmapping retailer_to_gram_cartproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cartproductmapping
    ADD CONSTRAINT retailer_to_gram_cartproductmapping_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_customercare retailer_to_gram_customercare_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_customercare
    ADD CONSTRAINT retailer_to_gram_customercare_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_note retailer_to_gram_note_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_note
    ADD CONSTRAINT retailer_to_gram_note_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_order retailer_to_gram_order_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_order_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_orderedproduct retailer_to_gram_orderedproduct_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproduct
    ADD CONSTRAINT retailer_to_gram_orderedproduct_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_orderedproductmapping retailer_to_gram_orderedproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproductmapping
    ADD CONSTRAINT retailer_to_gram_orderedproductmapping_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_gram_payment retailer_to_gram_payment_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_payment
    ADD CONSTRAINT retailer_to_gram_payment_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_cart retailer_to_sp_cart_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cart
    ADD CONSTRAINT retailer_to_sp_cart_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_cartproductmapping retailer_to_sp_cartproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cartproductmapping
    ADD CONSTRAINT retailer_to_sp_cartproductmapping_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_customercare retailer_to_sp_customercare_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_customercare
    ADD CONSTRAINT retailer_to_sp_customercare_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_note retailer_to_sp_note_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_note
    ADD CONSTRAINT retailer_to_sp_note_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_order retailer_to_sp_order_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_orderedproduct retailer_to_sp_orderedproduct_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproduct
    ADD CONSTRAINT retailer_to_sp_orderedproduct_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_orderedproductmapping retailer_to_sp_orderedproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproductmapping
    ADD CONSTRAINT retailer_to_sp_orderedproductmapping_pkey PRIMARY KEY (id);


--
-- Name: retailer_to_sp_payment retailer_to_sp_payment_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_payment
    ADD CONSTRAINT retailer_to_sp_payment_pkey PRIMARY KEY (id);


--
-- Name: shops_parentretailermapping shops_parentretailermapping_parent_id_retailer_id_b29bc423_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_parentretailermapping
    ADD CONSTRAINT shops_parentretailermapping_parent_id_retailer_id_b29bc423_uniq UNIQUE (parent_id, retailer_id);


--
-- Name: shops_parentretailermapping shops_parentretailermapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_parentretailermapping
    ADD CONSTRAINT shops_parentretailermapping_pkey PRIMARY KEY (id);


--
-- Name: shops_retailertype shops_retailertype_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_retailertype
    ADD CONSTRAINT shops_retailertype_pkey PRIMARY KEY (id);


--
-- Name: shops_shop shops_shop_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop
    ADD CONSTRAINT shops_shop_pkey PRIMARY KEY (id);


--
-- Name: shops_shop_related_users shops_shop_related_users_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop_related_users
    ADD CONSTRAINT shops_shop_related_users_pkey PRIMARY KEY (id);


--
-- Name: shops_shop_related_users shops_shop_related_users_shop_id_user_id_f6b02c0a_uniq; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop_related_users
    ADD CONSTRAINT shops_shop_related_users_shop_id_user_id_f6b02c0a_uniq UNIQUE (shop_id, user_id);


--
-- Name: shops_shopdocument shops_shopdocument_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shopdocument
    ADD CONSTRAINT shops_shopdocument_pkey PRIMARY KEY (id);


--
-- Name: shops_shopphoto shops_shopphoto_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shopphoto
    ADD CONSTRAINT shops_shopphoto_pkey PRIMARY KEY (id);


--
-- Name: shops_shoptype shops_shoptype_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shoptype
    ADD CONSTRAINT shops_shoptype_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_cart sp_to_gram_cart_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cart
    ADD CONSTRAINT sp_to_gram_cart_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_cartproductmapping sp_to_gram_cartproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cartproductmapping
    ADD CONSTRAINT sp_to_gram_cartproductmapping_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_order sp_to_gram_order_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_orderedproduct sp_to_gram_orderedproduct_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproduct
    ADD CONSTRAINT sp_to_gram_orderedproduct_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_orderedproductmapping sp_to_gram_orderedproductmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductmapping
    ADD CONSTRAINT sp_to_gram_orderedproductmapping_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_orderedproductreserved sp_to_gram_orderedproductreserved_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductreserved
    ADD CONSTRAINT sp_to_gram_orderedproductreserved_pkey PRIMARY KEY (id);


--
-- Name: sp_to_gram_spnote sp_to_gram_spnote_pkey; Type: CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_spnote
    ADD CONSTRAINT sp_to_gram_spnote_pkey PRIMARY KEY (id);


--
-- Name: account_emailaddress_email_03be32b2_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX account_emailaddress_email_03be32b2_like ON public.account_emailaddress USING btree (email varchar_pattern_ops);


--
-- Name: account_emailaddress_user_id_2c513194; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX account_emailaddress_user_id_2c513194 ON public.account_emailaddress USING btree (user_id);


--
-- Name: account_emailconfirmation_email_address_id_5b7f8c58; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX account_emailconfirmation_email_address_id_5b7f8c58 ON public.account_emailconfirmation USING btree (email_address_id);


--
-- Name: account_emailconfirmation_key_f43612bd_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX account_emailconfirmation_key_f43612bd_like ON public.account_emailconfirmation USING btree (key varchar_pattern_ops);


--
-- Name: accounts_user_groups_group_id_bd11a704; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX accounts_user_groups_group_id_bd11a704 ON public.accounts_user_groups USING btree (group_id);


--
-- Name: accounts_user_groups_user_id_52b62117; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX accounts_user_groups_user_id_52b62117 ON public.accounts_user_groups USING btree (user_id);


--
-- Name: accounts_user_phone_number_af3e1068_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX accounts_user_phone_number_af3e1068_like ON public.accounts_user USING btree (phone_number varchar_pattern_ops);


--
-- Name: accounts_user_user_permissions_permission_id_113bb443; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX accounts_user_user_permissions_permission_id_113bb443 ON public.accounts_user_user_permissions USING btree (permission_id);


--
-- Name: accounts_user_user_permissions_user_id_e4f0a161; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX accounts_user_user_permissions_user_id_e4f0a161 ON public.accounts_user_user_permissions USING btree (user_id);


--
-- Name: accounts_userdocument_user_id_29c3eb0b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX accounts_userdocument_user_id_29c3eb0b ON public.accounts_userdocument USING btree (user_id);


--
-- Name: addresses_address_city_id_04b2cff3; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_address_city_id_04b2cff3 ON public.addresses_address USING btree (city_id);


--
-- Name: addresses_address_shop_name_id_a76908fe; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_address_shop_name_id_a76908fe ON public.addresses_address USING btree (shop_name_id);


--
-- Name: addresses_address_state_id_e522e778; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_address_state_id_e522e778 ON public.addresses_address USING btree (state_id);


--
-- Name: addresses_area_city_id_8093d383; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_area_city_id_8093d383 ON public.addresses_area USING btree (city_id);


--
-- Name: addresses_city_country_id_d92ce02f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_city_country_id_d92ce02f ON public.addresses_city USING btree (country_id);


--
-- Name: addresses_city_state_id_a9ad09e8; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_city_state_id_a9ad09e8 ON public.addresses_city USING btree (state_id);


--
-- Name: addresses_state_country_id_af73cbb0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX addresses_state_country_id_af73cbb0 ON public.addresses_state USING btree (country_id);


--
-- Name: allauth_socialaccount_user_id_3b675ddd; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX allauth_socialaccount_user_id_3b675ddd ON public.allauth_socialaccount USING btree (user_id);


--
-- Name: allauth_socialapp_sites_site_id_26af3e5b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX allauth_socialapp_sites_site_id_26af3e5b ON public.allauth_socialapp_sites USING btree (site_id);


--
-- Name: allauth_socialapp_sites_socialapp_id_9b2489e9; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX allauth_socialapp_sites_socialapp_id_9b2489e9 ON public.allauth_socialapp_sites USING btree (socialapp_id);


--
-- Name: allauth_socialtoken_account_id_188497ae; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX allauth_socialtoken_account_id_188497ae ON public.allauth_socialtoken USING btree (account_id);


--
-- Name: allauth_socialtoken_app_id_f34fc476; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX allauth_socialtoken_app_id_f34fc476 ON public.allauth_socialtoken USING btree (app_id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: authtoken_token_key_10f0b77e_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX authtoken_token_key_10f0b77e_like ON public.authtoken_token USING btree (key varchar_pattern_ops);


--
-- Name: banner_bannerdata_banner_data_id_4e86c5fe; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerdata_banner_data_id_4e86c5fe ON public.banner_bannerdata USING btree (banner_data_id);


--
-- Name: banner_bannerdata_banner_data_order_750f17a9; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerdata_banner_data_order_750f17a9 ON public.banner_bannerdata USING btree (banner_data_order);


--
-- Name: banner_bannerdata_slot_id_17c528d7; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerdata_slot_id_17c528d7 ON public.banner_bannerdata USING btree (slot_id);


--
-- Name: banner_bannerposition_banner_position_order_a5264024; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerposition_banner_position_order_a5264024 ON public.banner_bannerposition USING btree (banner_position_order);


--
-- Name: banner_bannerposition_bannerslot_id_91f6b39d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerposition_bannerslot_id_91f6b39d ON public.banner_bannerposition USING btree (bannerslot_id);


--
-- Name: banner_bannerposition_page_id_64226b4c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerposition_page_id_64226b4c ON public.banner_bannerposition USING btree (page_id);


--
-- Name: banner_bannerslot_name_0ce74ed9_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerslot_name_0ce74ed9_like ON public.banner_bannerslot USING btree (name varchar_pattern_ops);


--
-- Name: banner_bannerslot_page_id_2c9e527c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX banner_bannerslot_page_id_2c9e527c ON public.banner_bannerslot USING btree (page_id);


--
-- Name: brand_brand_brand_parent_id_660df75f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_brand_brand_parent_id_660df75f ON public.brand_brand USING btree (brand_parent_id);


--
-- Name: brand_brand_brand_slug_6f985c41; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_brand_brand_slug_6f985c41 ON public.brand_brand USING btree (brand_slug);


--
-- Name: brand_brand_brand_slug_6f985c41_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_brand_brand_slug_6f985c41_like ON public.brand_brand USING btree (brand_slug varchar_pattern_ops);


--
-- Name: brand_branddata_brand_data_id_880a904d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_branddata_brand_data_id_880a904d ON public.brand_branddata USING btree (brand_data_id);


--
-- Name: brand_branddata_brand_data_order_86a50852; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_branddata_brand_data_order_86a50852 ON public.brand_branddata USING btree (brand_data_order);


--
-- Name: brand_branddata_slot_id_6e3f43c3; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_branddata_slot_id_6e3f43c3 ON public.brand_branddata USING btree (slot_id);


--
-- Name: brand_brandposition_brand_position_order_e382ae4c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_brandposition_brand_position_order_e382ae4c ON public.brand_brandposition USING btree (brand_position_order);


--
-- Name: brand_vendor_city_id_c411df76; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_vendor_city_id_c411df76 ON public.brand_vendor USING btree (city_id);


--
-- Name: brand_vendor_state_id_47e1bd64; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX brand_vendor_state_id_47e1bd64 ON public.brand_vendor USING btree (state_id);


--
-- Name: categories_category_category_name_9934dd1b_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_category_category_name_9934dd1b_like ON public.categories_category USING btree (category_name varchar_pattern_ops);


--
-- Name: categories_category_category_parent_id_deb82704; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_category_category_parent_id_deb82704 ON public.categories_category USING btree (category_parent_id);


--
-- Name: categories_category_category_sku_part_3cbd32ab_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_category_category_sku_part_3cbd32ab_like ON public.categories_category USING btree (category_sku_part varchar_pattern_ops);


--
-- Name: categories_category_category_slug_066e1815_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_category_category_slug_066e1815_like ON public.categories_category USING btree (category_slug varchar_pattern_ops);


--
-- Name: categories_categorydata_category_data_id_f5565bf2; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_categorydata_category_data_id_f5565bf2 ON public.categories_categorydata USING btree (category_data_id);


--
-- Name: categories_categorydata_category_data_order_e66120b0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_categorydata_category_data_order_e66120b0 ON public.categories_categorydata USING btree (category_data_order);


--
-- Name: categories_categorydata_category_pos_id_df2f1117; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_categorydata_category_pos_id_df2f1117 ON public.categories_categorydata USING btree (category_pos_id);


--
-- Name: categories_categoryposation_category_posation_order_95bdeeac; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX categories_categoryposation_category_posation_order_95bdeeac ON public.categories_categoryposation USING btree (category_posation_order);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: django_site_domain_a2e37b91_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX django_site_domain_a2e37b91_like ON public.django_site USING btree (domain varchar_pattern_ops);


--
-- Name: gram_to_brand_brandnote_grn_order_id_976650a3; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_brandnote_grn_order_id_976650a3 ON public.gram_to_brand_brandnote USING btree (grn_order_id);


--
-- Name: gram_to_brand_brandnote_last_modified_by_id_c7ed17b3; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_brandnote_last_modified_by_id_c7ed17b3 ON public.gram_to_brand_brandnote USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_brandnote_order_id_b3511b90; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_brandnote_order_id_b3511b90 ON public.gram_to_brand_brandnote USING btree (order_id);


--
-- Name: gram_to_brand_cart_brand_id_31d2b48d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_brand_id_31d2b48d ON public.gram_to_brand_cart USING btree (brand_id);


--
-- Name: gram_to_brand_cart_gf_billing_address_id_11a93f68; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_gf_billing_address_id_11a93f68 ON public.gram_to_brand_cart USING btree (gf_billing_address_id);


--
-- Name: gram_to_brand_cart_gf_shipping_address_id_775b7e1d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_gf_shipping_address_id_775b7e1d ON public.gram_to_brand_cart USING btree (gf_shipping_address_id);


--
-- Name: gram_to_brand_cart_last_modified_by_id_f5d9393f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_last_modified_by_id_f5d9393f ON public.gram_to_brand_cart USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_cart_po_message_id_efd7dc51; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_po_message_id_efd7dc51 ON public.gram_to_brand_cart USING btree (po_message_id);


--
-- Name: gram_to_brand_cart_po_raised_by_id_6c46c9e1; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_po_raised_by_id_6c46c9e1 ON public.gram_to_brand_cart USING btree (po_raised_by_id);


--
-- Name: gram_to_brand_cart_shop_id_eec83ebf; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_shop_id_eec83ebf ON public.gram_to_brand_cart USING btree (shop_id);


--
-- Name: gram_to_brand_cart_supplier_name_id_f692b789; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_supplier_name_id_f692b789 ON public.gram_to_brand_cart USING btree (supplier_name_id);


--
-- Name: gram_to_brand_cart_supplier_state_id_bbd262da; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cart_supplier_state_id_bbd262da ON public.gram_to_brand_cart USING btree (supplier_state_id);


--
-- Name: gram_to_brand_cartproductmapping_cart_id_e33c9b36; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cartproductmapping_cart_id_e33c9b36 ON public.gram_to_brand_cartproductmapping USING btree (cart_id);


--
-- Name: gram_to_brand_cartproductmapping_cart_product_id_44cedeed; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_cartproductmapping_cart_product_id_44cedeed ON public.gram_to_brand_cartproductmapping USING btree (cart_product_id);


--
-- Name: gram_to_brand_grnorder_last_modified_by_id_4f77c029; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorder_last_modified_by_id_4f77c029 ON public.gram_to_brand_grnorder USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_grnorder_order_id_a346e896; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorder_order_id_a346e896 ON public.gram_to_brand_grnorder USING btree (order_id);


--
-- Name: gram_to_brand_grnorder_order_item_id_1ce00752; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorder_order_item_id_1ce00752 ON public.gram_to_brand_grnorder USING btree (order_item_id);


--
-- Name: gram_to_brand_grnorderprod_last_modified_by_id_ccd70c3f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderprod_last_modified_by_id_ccd70c3f ON public.gram_to_brand_grnorderproducthistory USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_grnorderprod_last_modified_by_id_fea4295a; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderprod_last_modified_by_id_fea4295a ON public.gram_to_brand_grnorderproductmapping USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_grnorderproducthistory_grn_order_id_08171666; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderproducthistory_grn_order_id_08171666 ON public.gram_to_brand_grnorderproducthistory USING btree (grn_order_id);


--
-- Name: gram_to_brand_grnorderproducthistory_order_id_38bc0890; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderproducthistory_order_id_38bc0890 ON public.gram_to_brand_grnorderproducthistory USING btree (order_id);


--
-- Name: gram_to_brand_grnorderproducthistory_order_item_id_ac417f8f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderproducthistory_order_item_id_ac417f8f ON public.gram_to_brand_grnorderproducthistory USING btree (order_item_id);


--
-- Name: gram_to_brand_grnorderproducthistory_product_id_f6f5af96; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderproducthistory_product_id_f6f5af96 ON public.gram_to_brand_grnorderproducthistory USING btree (product_id);


--
-- Name: gram_to_brand_grnorderproductmapping_grn_order_id_b06c17ed; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderproductmapping_grn_order_id_b06c17ed ON public.gram_to_brand_grnorderproductmapping USING btree (grn_order_id);


--
-- Name: gram_to_brand_grnorderproductmapping_product_id_361def72; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_grnorderproductmapping_product_id_361def72 ON public.gram_to_brand_grnorderproductmapping USING btree (product_id);


--
-- Name: gram_to_brand_order_billing_address_id_9d176a19; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_billing_address_id_9d176a19 ON public.gram_to_brand_order USING btree (billing_address_id);


--
-- Name: gram_to_brand_order_last_modified_by_id_3ee5370c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_last_modified_by_id_3ee5370c ON public.gram_to_brand_order USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_order_ordered_by_id_3a6b0324; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_ordered_by_id_3a6b0324 ON public.gram_to_brand_order USING btree (ordered_by_id);


--
-- Name: gram_to_brand_order_ordered_cart_id_7c60e36b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_ordered_cart_id_7c60e36b ON public.gram_to_brand_order USING btree (ordered_cart_id);


--
-- Name: gram_to_brand_order_received_by_id_fd0a8f7e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_received_by_id_fd0a8f7e ON public.gram_to_brand_order USING btree (received_by_id);


--
-- Name: gram_to_brand_order_shipping_address_id_9f9d66c0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_shipping_address_id_9f9d66c0 ON public.gram_to_brand_order USING btree (shipping_address_id);


--
-- Name: gram_to_brand_order_shop_id_0dcee062; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_order_shop_id_0dcee062 ON public.gram_to_brand_order USING btree (shop_id);


--
-- Name: gram_to_brand_orderedprodu_order_product_reserved_id_7b7d2f5a; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderedprodu_order_product_reserved_id_7b7d2f5a ON public.gram_to_brand_orderedproductreserved USING btree (order_product_reserved_id);


--
-- Name: gram_to_brand_orderedproductreserved_cart_id_7c851e22; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderedproductreserved_cart_id_7c851e22 ON public.gram_to_brand_orderedproductreserved USING btree (cart_id);


--
-- Name: gram_to_brand_orderedproductreserved_product_id_3750ee6c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderedproductreserved_product_id_3750ee6c ON public.gram_to_brand_orderedproductreserved USING btree (product_id);


--
-- Name: gram_to_brand_orderhistory_billing_address_id_a8520355; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_billing_address_id_a8520355 ON public.gram_to_brand_orderhistory USING btree (billing_address_id);


--
-- Name: gram_to_brand_orderhistory_buyer_shop_id_bfea710e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_buyer_shop_id_bfea710e ON public.gram_to_brand_orderhistory USING btree (buyer_shop_id);


--
-- Name: gram_to_brand_orderhistory_last_modified_by_id_d57f7154; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_last_modified_by_id_d57f7154 ON public.gram_to_brand_orderhistory USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_orderhistory_ordered_by_id_ac4a43bc; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_ordered_by_id_ac4a43bc ON public.gram_to_brand_orderhistory USING btree (ordered_by_id);


--
-- Name: gram_to_brand_orderhistory_ordered_cart_id_eb53e26e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_ordered_cart_id_eb53e26e ON public.gram_to_brand_orderhistory USING btree (ordered_cart_id);


--
-- Name: gram_to_brand_orderhistory_received_by_id_8fdc3115; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_received_by_id_8fdc3115 ON public.gram_to_brand_orderhistory USING btree (received_by_id);


--
-- Name: gram_to_brand_orderhistory_seller_shop_id_2c321d21; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_seller_shop_id_2c321d21 ON public.gram_to_brand_orderhistory USING btree (seller_shop_id);


--
-- Name: gram_to_brand_orderhistory_shipping_address_id_096ca4ec; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderhistory_shipping_address_id_096ca4ec ON public.gram_to_brand_orderhistory USING btree (shipping_address_id);


--
-- Name: gram_to_brand_orderitem_last_modified_by_id_b4f9089f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderitem_last_modified_by_id_b4f9089f ON public.gram_to_brand_orderitem USING btree (last_modified_by_id);


--
-- Name: gram_to_brand_orderitem_order_id_49494a20; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderitem_order_id_49494a20 ON public.gram_to_brand_orderitem USING btree (order_id);


--
-- Name: gram_to_brand_orderitem_ordered_product_id_44c5b4a8; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_orderitem_ordered_product_id_44c5b4a8 ON public.gram_to_brand_orderitem USING btree (ordered_product_id);


--
-- Name: gram_to_brand_picklist_cart_id_8b2c917c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_picklist_cart_id_8b2c917c ON public.gram_to_brand_picklist USING btree (cart_id);


--
-- Name: gram_to_brand_picklist_order_id_61071bf2; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_picklist_order_id_61071bf2 ON public.gram_to_brand_picklist USING btree (order_id);


--
-- Name: gram_to_brand_picklistitems_grn_order_id_9a26fdff; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_picklistitems_grn_order_id_9a26fdff ON public.gram_to_brand_picklistitems USING btree (grn_order_id);


--
-- Name: gram_to_brand_picklistitems_pick_list_id_2627ea46; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_picklistitems_pick_list_id_2627ea46 ON public.gram_to_brand_picklistitems USING btree (pick_list_id);


--
-- Name: gram_to_brand_picklistitems_product_id_1d553e21; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_picklistitems_product_id_1d553e21 ON public.gram_to_brand_picklistitems USING btree (product_id);


--
-- Name: gram_to_brand_po_message_created_by_id_f4866384; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX gram_to_brand_po_message_created_by_id_f4866384 ON public.gram_to_brand_po_message USING btree (created_by_id);


--
-- Name: products_packagesize_pack_size_name_103cd6ef_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_packagesize_pack_size_name_103cd6ef_like ON public.products_packagesize USING btree (pack_size_name varchar_pattern_ops);


--
-- Name: products_product_product_brand_id_1d698d6e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_product_product_brand_id_1d698d6e ON public.products_product USING btree (product_brand_id);


--
-- Name: products_product_product_gf_code_5484d0a5_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_product_product_gf_code_5484d0a5_like ON public.products_product USING btree (product_gf_code varchar_pattern_ops);


--
-- Name: products_product_product_sku_7fc65a4b_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_product_product_sku_7fc65a4b_like ON public.products_product USING btree (product_sku varchar_pattern_ops);


--
-- Name: products_product_product_slug_fbb5f864; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_product_product_slug_fbb5f864 ON public.products_product USING btree (product_slug);


--
-- Name: products_product_product_slug_fbb5f864_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_product_product_slug_fbb5f864_like ON public.products_product USING btree (product_slug varchar_pattern_ops);


--
-- Name: products_productcategory_category_id_89ea68e5; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productcategory_category_id_89ea68e5 ON public.products_productcategory USING btree (category_id);


--
-- Name: products_productcategory_product_id_acd5dd19; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productcategory_product_id_acd5dd19 ON public.products_productcategory USING btree (product_id);


--
-- Name: products_productcategoryhistory_category_id_c4fb4b4b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productcategoryhistory_category_id_c4fb4b4b ON public.products_productcategoryhistory USING btree (category_id);


--
-- Name: products_productcategoryhistory_product_id_090e0c13; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productcategoryhistory_product_id_090e0c13 ON public.products_productcategoryhistory USING btree (product_id);


--
-- Name: products_productimage_product_id_e747596a; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productimage_product_id_e747596a ON public.products_productimage USING btree (product_id);


--
-- Name: products_productoption_color_id_e61e2def; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_color_id_e61e2def ON public.products_productoption USING btree (color_id);


--
-- Name: products_productoption_flavor_id_4e6120f5; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_flavor_id_4e6120f5 ON public.products_productoption USING btree (flavor_id);


--
-- Name: products_productoption_fragrance_id_c8c243de; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_fragrance_id_c8c243de ON public.products_productoption USING btree (fragrance_id);


--
-- Name: products_productoption_package_size_id_e309b1aa; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_package_size_id_e309b1aa ON public.products_productoption USING btree (package_size_id);


--
-- Name: products_productoption_product_id_6dc2057d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_product_id_6dc2057d ON public.products_productoption USING btree (product_id);


--
-- Name: products_productoption_size_id_93ade64f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_size_id_93ade64f ON public.products_productoption USING btree (size_id);


--
-- Name: products_productoption_weight_id_2bf64ad6; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productoption_weight_id_2bf64ad6 ON public.products_productoption USING btree (weight_id);


--
-- Name: products_productprice_area_id_f942f99b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productprice_area_id_f942f99b ON public.products_productprice USING btree (area_id);


--
-- Name: products_productprice_city_id_86b4ddd8; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productprice_city_id_86b4ddd8 ON public.products_productprice USING btree (city_id);


--
-- Name: products_productprice_product_id_efef3000; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productprice_product_id_efef3000 ON public.products_productprice USING btree (product_id);


--
-- Name: products_productprice_shop_id_2ec945ae; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productprice_shop_id_2ec945ae ON public.products_productprice USING btree (shop_id);


--
-- Name: products_productpricecsv_area_id_3cc79290; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productpricecsv_area_id_3cc79290 ON public.products_productpricecsv USING btree (area_id);


--
-- Name: products_productpricecsv_city_id_987b5623; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productpricecsv_city_id_987b5623 ON public.products_productpricecsv USING btree (city_id);


--
-- Name: products_productpricecsv_country_id_29c73281; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productpricecsv_country_id_29c73281 ON public.products_productpricecsv USING btree (country_id);


--
-- Name: products_productpricecsv_states_id_8de350d1; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productpricecsv_states_id_8de350d1 ON public.products_productpricecsv USING btree (states_id);


--
-- Name: products_producttaxmapping_product_id_9d39623c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_producttaxmapping_product_id_9d39623c ON public.products_producttaxmapping USING btree (product_id);


--
-- Name: products_producttaxmapping_tax_id_18a14597; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_producttaxmapping_tax_id_18a14597 ON public.products_producttaxmapping USING btree (tax_id);


--
-- Name: products_productvendormapping_product_id_4831243c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productvendormapping_product_id_4831243c ON public.products_productvendormapping USING btree (product_id);


--
-- Name: products_productvendormapping_vendor_id_d9bc27fc; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_productvendormapping_vendor_id_d9bc27fc ON public.products_productvendormapping USING btree (vendor_id);


--
-- Name: products_size_size_name_c69af489_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_size_size_name_c69af489_like ON public.products_size USING btree (size_name varchar_pattern_ops);


--
-- Name: products_weight_weight_name_cb0ed944_like; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX products_weight_weight_name_cb0ed944_like ON public.products_weight USING btree (weight_name varchar_pattern_ops);


--
-- Name: retailer_to_gram_cart_last_modified_by_id_1ca90b12; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_cart_last_modified_by_id_1ca90b12 ON public.retailer_to_gram_cart USING btree (last_modified_by_id);


--
-- Name: retailer_to_gram_cartproductmapping_cart_id_fe0d96a5; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_cartproductmapping_cart_id_fe0d96a5 ON public.retailer_to_gram_cartproductmapping USING btree (cart_id);


--
-- Name: retailer_to_gram_cartproductmapping_cart_product_id_69584057; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_cartproductmapping_cart_product_id_69584057 ON public.retailer_to_gram_cartproductmapping USING btree (cart_product_id);


--
-- Name: retailer_to_gram_customercare_order_id_id_ce80023f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_customercare_order_id_id_ce80023f ON public.retailer_to_gram_customercare USING btree (order_id_id);


--
-- Name: retailer_to_gram_note_last_modified_by_id_12493eb0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_note_last_modified_by_id_12493eb0 ON public.retailer_to_gram_note USING btree (last_modified_by_id);


--
-- Name: retailer_to_gram_note_order_id_92a72968; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_note_order_id_92a72968 ON public.retailer_to_gram_note USING btree (order_id);


--
-- Name: retailer_to_gram_note_ordered_product_id_3ab64437; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_note_ordered_product_id_3ab64437 ON public.retailer_to_gram_note USING btree (ordered_product_id);


--
-- Name: retailer_to_gram_order_billing_address_id_2a9ce80d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_billing_address_id_2a9ce80d ON public.retailer_to_gram_order USING btree (billing_address_id);


--
-- Name: retailer_to_gram_order_buyer_shop_id_720a6f53; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_buyer_shop_id_720a6f53 ON public.retailer_to_gram_order USING btree (buyer_shop_id);


--
-- Name: retailer_to_gram_order_last_modified_by_id_e6c3d296; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_last_modified_by_id_e6c3d296 ON public.retailer_to_gram_order USING btree (last_modified_by_id);


--
-- Name: retailer_to_gram_order_ordered_by_id_5f029772; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_ordered_by_id_5f029772 ON public.retailer_to_gram_order USING btree (ordered_by_id);


--
-- Name: retailer_to_gram_order_ordered_cart_id_0993e56e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_ordered_cart_id_0993e56e ON public.retailer_to_gram_order USING btree (ordered_cart_id);


--
-- Name: retailer_to_gram_order_received_by_id_e1850936; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_received_by_id_e1850936 ON public.retailer_to_gram_order USING btree (received_by_id);


--
-- Name: retailer_to_gram_order_seller_shop_id_739a7026; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_seller_shop_id_739a7026 ON public.retailer_to_gram_order USING btree (seller_shop_id);


--
-- Name: retailer_to_gram_order_shipping_address_id_4f8d3b5a; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_order_shipping_address_id_4f8d3b5a ON public.retailer_to_gram_order USING btree (shipping_address_id);


--
-- Name: retailer_to_gram_orderedpr_last_modified_by_id_c14095fe; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedpr_last_modified_by_id_c14095fe ON public.retailer_to_gram_orderedproductmapping USING btree (last_modified_by_id);


--
-- Name: retailer_to_gram_orderedpr_ordered_product_id_b4829f7d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedpr_ordered_product_id_b4829f7d ON public.retailer_to_gram_orderedproductmapping USING btree (ordered_product_id);


--
-- Name: retailer_to_gram_orderedproduct_last_modified_by_id_86a72784; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedproduct_last_modified_by_id_86a72784 ON public.retailer_to_gram_orderedproduct USING btree (last_modified_by_id);


--
-- Name: retailer_to_gram_orderedproduct_order_id_9ebac3d0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedproduct_order_id_9ebac3d0 ON public.retailer_to_gram_orderedproduct USING btree (order_id);


--
-- Name: retailer_to_gram_orderedproduct_received_by_id_41ae19b2; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedproduct_received_by_id_41ae19b2 ON public.retailer_to_gram_orderedproduct USING btree (received_by_id);


--
-- Name: retailer_to_gram_orderedproduct_shipped_by_id_415524e6; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedproduct_shipped_by_id_415524e6 ON public.retailer_to_gram_orderedproduct USING btree (shipped_by_id);


--
-- Name: retailer_to_gram_orderedproductmapping_product_id_ed795395; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_orderedproductmapping_product_id_ed795395 ON public.retailer_to_gram_orderedproductmapping USING btree (product_id);


--
-- Name: retailer_to_gram_payment_order_id_id_a3f9d00b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_gram_payment_order_id_id_a3f9d00b ON public.retailer_to_gram_payment USING btree (order_id_id);


--
-- Name: retailer_to_sp_cart_last_modified_by_id_2464780e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_cart_last_modified_by_id_2464780e ON public.retailer_to_sp_cart USING btree (last_modified_by_id);


--
-- Name: retailer_to_sp_cartproductmapping_cart_id_35aa1297; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_cartproductmapping_cart_id_35aa1297 ON public.retailer_to_sp_cartproductmapping USING btree (cart_id);


--
-- Name: retailer_to_sp_cartproductmapping_cart_product_id_b52f6ff1; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_cartproductmapping_cart_product_id_b52f6ff1 ON public.retailer_to_sp_cartproductmapping USING btree (cart_product_id);


--
-- Name: retailer_to_sp_customercare_order_id_id_3c80587a; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_customercare_order_id_id_3c80587a ON public.retailer_to_sp_customercare USING btree (order_id_id);


--
-- Name: retailer_to_sp_note_last_modified_by_id_0fc126c4; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_note_last_modified_by_id_0fc126c4 ON public.retailer_to_sp_note USING btree (last_modified_by_id);


--
-- Name: retailer_to_sp_note_order_id_2ea61fcd; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_note_order_id_2ea61fcd ON public.retailer_to_sp_note USING btree (order_id);


--
-- Name: retailer_to_sp_note_ordered_product_id_c6c698ba; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_note_ordered_product_id_c6c698ba ON public.retailer_to_sp_note USING btree (ordered_product_id);


--
-- Name: retailer_to_sp_order_billing_address_id_5361f86b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_billing_address_id_5361f86b ON public.retailer_to_sp_order USING btree (billing_address_id);


--
-- Name: retailer_to_sp_order_buyer_shop_id_cdd19a74; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_buyer_shop_id_cdd19a74 ON public.retailer_to_sp_order USING btree (buyer_shop_id);


--
-- Name: retailer_to_sp_order_last_modified_by_id_50939d56; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_last_modified_by_id_50939d56 ON public.retailer_to_sp_order USING btree (last_modified_by_id);


--
-- Name: retailer_to_sp_order_ordered_by_id_366d32bc; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_ordered_by_id_366d32bc ON public.retailer_to_sp_order USING btree (ordered_by_id);


--
-- Name: retailer_to_sp_order_ordered_cart_id_c9dc11fa; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_ordered_cart_id_c9dc11fa ON public.retailer_to_sp_order USING btree (ordered_cart_id);


--
-- Name: retailer_to_sp_order_received_by_id_27c7bb7d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_received_by_id_27c7bb7d ON public.retailer_to_sp_order USING btree (received_by_id);


--
-- Name: retailer_to_sp_order_seller_shop_id_0c71a300; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_seller_shop_id_0c71a300 ON public.retailer_to_sp_order USING btree (seller_shop_id);


--
-- Name: retailer_to_sp_order_shipping_address_id_aa615dea; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_order_shipping_address_id_aa615dea ON public.retailer_to_sp_order USING btree (shipping_address_id);


--
-- Name: retailer_to_sp_orderedprod_last_modified_by_id_73bebc82; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedprod_last_modified_by_id_73bebc82 ON public.retailer_to_sp_orderedproductmapping USING btree (last_modified_by_id);


--
-- Name: retailer_to_sp_orderedprod_ordered_product_id_a597c9db; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedprod_ordered_product_id_a597c9db ON public.retailer_to_sp_orderedproductmapping USING btree (ordered_product_id);


--
-- Name: retailer_to_sp_orderedproduct_last_modified_by_id_65925327; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedproduct_last_modified_by_id_65925327 ON public.retailer_to_sp_orderedproduct USING btree (last_modified_by_id);


--
-- Name: retailer_to_sp_orderedproduct_order_id_532bc99c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedproduct_order_id_532bc99c ON public.retailer_to_sp_orderedproduct USING btree (order_id);


--
-- Name: retailer_to_sp_orderedproduct_received_by_id_8bd3c1c4; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedproduct_received_by_id_8bd3c1c4 ON public.retailer_to_sp_orderedproduct USING btree (received_by_id);


--
-- Name: retailer_to_sp_orderedproduct_shipped_by_id_f014d527; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedproduct_shipped_by_id_f014d527 ON public.retailer_to_sp_orderedproduct USING btree (shipped_by_id);


--
-- Name: retailer_to_sp_orderedproductmapping_product_id_54dd513b; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_orderedproductmapping_product_id_54dd513b ON public.retailer_to_sp_orderedproductmapping USING btree (product_id);


--
-- Name: retailer_to_sp_payment_order_id_id_206e64b0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX retailer_to_sp_payment_order_id_id_206e64b0 ON public.retailer_to_sp_payment USING btree (order_id_id);


--
-- Name: shops_parentretailermapping_parent_id_385afda4; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_parentretailermapping_parent_id_385afda4 ON public.shops_parentretailermapping USING btree (parent_id);


--
-- Name: shops_parentretailermapping_retailer_id_48f7b6d0; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_parentretailermapping_retailer_id_48f7b6d0 ON public.shops_parentretailermapping USING btree (retailer_id);


--
-- Name: shops_shop_related_users_shop_id_3601acae; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shop_related_users_shop_id_3601acae ON public.shops_shop_related_users USING btree (shop_id);


--
-- Name: shops_shop_related_users_user_id_ecee493d; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shop_related_users_user_id_ecee493d ON public.shops_shop_related_users USING btree (user_id);


--
-- Name: shops_shop_shop_owner_id_3a01cb19; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shop_shop_owner_id_3a01cb19 ON public.shops_shop USING btree (shop_owner_id);


--
-- Name: shops_shop_shop_type_id_8f5bca08; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shop_shop_type_id_8f5bca08 ON public.shops_shop USING btree (shop_type_id);


--
-- Name: shops_shopdocument_shop_name_id_b1644942; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shopdocument_shop_name_id_b1644942 ON public.shops_shopdocument USING btree (shop_name_id);


--
-- Name: shops_shopphoto_shop_name_id_d9efdb28; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shopphoto_shop_name_id_d9efdb28 ON public.shops_shopphoto USING btree (shop_name_id);


--
-- Name: shops_shoptype_shop_sub_type_id_c9d3a779; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX shops_shoptype_shop_sub_type_id_c9d3a779 ON public.shops_shoptype USING btree (shop_sub_type_id);


--
-- Name: sp_to_gram_cart_last_modified_by_id_39fdf725; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_cart_last_modified_by_id_39fdf725 ON public.sp_to_gram_cart USING btree (last_modified_by_id);


--
-- Name: sp_to_gram_cart_po_raised_by_id_fca43b07; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_cart_po_raised_by_id_fca43b07 ON public.sp_to_gram_cart USING btree (po_raised_by_id);


--
-- Name: sp_to_gram_cart_shop_id_e8ed569c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_cart_shop_id_e8ed569c ON public.sp_to_gram_cart USING btree (shop_id);


--
-- Name: sp_to_gram_cartproductmapping_cart_id_b5f0d261; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_cartproductmapping_cart_id_b5f0d261 ON public.sp_to_gram_cartproductmapping USING btree (cart_id);


--
-- Name: sp_to_gram_cartproductmapping_cart_product_id_385ec226; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_cartproductmapping_cart_product_id_385ec226 ON public.sp_to_gram_cartproductmapping USING btree (cart_product_id);


--
-- Name: sp_to_gram_order_billing_address_id_c2ec935f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_order_billing_address_id_c2ec935f ON public.sp_to_gram_order USING btree (billing_address_id);


--
-- Name: sp_to_gram_order_last_modified_by_id_e340f48f; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_order_last_modified_by_id_e340f48f ON public.sp_to_gram_order USING btree (last_modified_by_id);


--
-- Name: sp_to_gram_order_ordered_by_id_bb437ba6; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_order_ordered_by_id_bb437ba6 ON public.sp_to_gram_order USING btree (ordered_by_id);


--
-- Name: sp_to_gram_order_ordered_cart_id_deab1bca; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_order_ordered_cart_id_deab1bca ON public.sp_to_gram_order USING btree (ordered_cart_id);


--
-- Name: sp_to_gram_order_received_by_id_25eec96e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_order_received_by_id_25eec96e ON public.sp_to_gram_order USING btree (received_by_id);


--
-- Name: sp_to_gram_order_shipping_address_id_87126904; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_order_shipping_address_id_87126904 ON public.sp_to_gram_order USING btree (shipping_address_id);


--
-- Name: sp_to_gram_orderedproduct_last_modified_by_id_1db1474c; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproduct_last_modified_by_id_1db1474c ON public.sp_to_gram_orderedproduct USING btree (last_modified_by_id);


--
-- Name: sp_to_gram_orderedproduct_order_id_836db601; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproduct_order_id_836db601 ON public.sp_to_gram_orderedproduct USING btree (order_id);


--
-- Name: sp_to_gram_orderedproduct_received_by_id_57a2d639; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproduct_received_by_id_57a2d639 ON public.sp_to_gram_orderedproduct USING btree (received_by_id);


--
-- Name: sp_to_gram_orderedproduct_shipped_by_id_e9504c74; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproduct_shipped_by_id_e9504c74 ON public.sp_to_gram_orderedproduct USING btree (shipped_by_id);


--
-- Name: sp_to_gram_orderedproductmapping_last_modified_by_id_fc82ae35; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproductmapping_last_modified_by_id_fc82ae35 ON public.sp_to_gram_orderedproductmapping USING btree (last_modified_by_id);


--
-- Name: sp_to_gram_orderedproductmapping_ordered_product_id_2ecd7ed2; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproductmapping_ordered_product_id_2ecd7ed2 ON public.sp_to_gram_orderedproductmapping USING btree (ordered_product_id);


--
-- Name: sp_to_gram_orderedproductmapping_product_id_b716f00e; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproductmapping_product_id_b716f00e ON public.sp_to_gram_orderedproductmapping USING btree (product_id);


--
-- Name: sp_to_gram_orderedproductr_order_product_reserved_id_6a000eee; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproductr_order_product_reserved_id_6a000eee ON public.sp_to_gram_orderedproductreserved USING btree (order_product_reserved_id);


--
-- Name: sp_to_gram_orderedproductreserved_cart_id_3a10e771; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproductreserved_cart_id_3a10e771 ON public.sp_to_gram_orderedproductreserved USING btree (cart_id);


--
-- Name: sp_to_gram_orderedproductreserved_product_id_b05783cb; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_orderedproductreserved_product_id_b05783cb ON public.sp_to_gram_orderedproductreserved USING btree (product_id);


--
-- Name: sp_to_gram_spnote_grn_order_id_ac835aa9; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_spnote_grn_order_id_ac835aa9 ON public.sp_to_gram_spnote USING btree (grn_order_id);


--
-- Name: sp_to_gram_spnote_last_modified_by_id_a6400570; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_spnote_last_modified_by_id_a6400570 ON public.sp_to_gram_spnote USING btree (last_modified_by_id);


--
-- Name: sp_to_gram_spnote_order_id_7fb63660; Type: INDEX; Schema: public; Owner: gramfac18
--

CREATE INDEX sp_to_gram_spnote_order_id_7fb63660 ON public.sp_to_gram_spnote USING btree (order_id);


--
-- Name: account_emailaddress account_emailaddress_user_id_2c513194_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailaddress
    ADD CONSTRAINT account_emailaddress_user_id_2c513194_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: account_emailconfirmation account_emailconfirm_email_address_id_5b7f8c58_fk_account_e; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.account_emailconfirmation
    ADD CONSTRAINT account_emailconfirm_email_address_id_5b7f8c58_fk_account_e FOREIGN KEY (email_address_id) REFERENCES public.account_emailaddress(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_groups accounts_user_groups_group_id_bd11a704_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_group_id_bd11a704_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_groups accounts_user_groups_user_id_52b62117_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_groups
    ADD CONSTRAINT accounts_user_groups_user_id_52b62117_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_user_permissions accounts_user_user_p_permission_id_113bb443_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_p_permission_id_113bb443_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_user_user_permissions accounts_user_user_p_user_id_e4f0a161_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_user_user_permissions
    ADD CONSTRAINT accounts_user_user_p_user_id_e4f0a161_fk_accounts_ FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounts_userdocument accounts_userdocument_user_id_29c3eb0b_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.accounts_userdocument
    ADD CONSTRAINT accounts_userdocument_user_id_29c3eb0b_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_address addresses_address_city_id_04b2cff3_fk_addresses_city_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_address
    ADD CONSTRAINT addresses_address_city_id_04b2cff3_fk_addresses_city_id FOREIGN KEY (city_id) REFERENCES public.addresses_city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_address addresses_address_shop_name_id_a76908fe_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_address
    ADD CONSTRAINT addresses_address_shop_name_id_a76908fe_fk_shops_shop_id FOREIGN KEY (shop_name_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_address addresses_address_state_id_e522e778_fk_addresses_state_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_address
    ADD CONSTRAINT addresses_address_state_id_e522e778_fk_addresses_state_id FOREIGN KEY (state_id) REFERENCES public.addresses_state(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_area addresses_area_city_id_8093d383_fk_addresses_city_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_area
    ADD CONSTRAINT addresses_area_city_id_8093d383_fk_addresses_city_id FOREIGN KEY (city_id) REFERENCES public.addresses_city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_city addresses_city_country_id_d92ce02f_fk_addresses_country_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_city
    ADD CONSTRAINT addresses_city_country_id_d92ce02f_fk_addresses_country_id FOREIGN KEY (country_id) REFERENCES public.addresses_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_city addresses_city_state_id_a9ad09e8_fk_addresses_state_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_city
    ADD CONSTRAINT addresses_city_state_id_a9ad09e8_fk_addresses_state_id FOREIGN KEY (state_id) REFERENCES public.addresses_state(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_invoicecitymapping addresses_invoicecit_city_id_b81200d1_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_invoicecitymapping
    ADD CONSTRAINT addresses_invoicecit_city_id_b81200d1_fk_addresses FOREIGN KEY (city_id) REFERENCES public.addresses_city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: addresses_state addresses_state_country_id_af73cbb0_fk_addresses_country_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.addresses_state
    ADD CONSTRAINT addresses_state_country_id_af73cbb0_fk_addresses_country_id FOREIGN KEY (country_id) REFERENCES public.addresses_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: allauth_socialaccount allauth_socialaccount_user_id_3b675ddd_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialaccount
    ADD CONSTRAINT allauth_socialaccount_user_id_3b675ddd_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: allauth_socialapp_sites allauth_socialapp_si_socialapp_id_9b2489e9_fk_allauth_s; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp_sites
    ADD CONSTRAINT allauth_socialapp_si_socialapp_id_9b2489e9_fk_allauth_s FOREIGN KEY (socialapp_id) REFERENCES public.allauth_socialapp(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: allauth_socialapp_sites allauth_socialapp_sites_site_id_26af3e5b_fk_django_site_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialapp_sites
    ADD CONSTRAINT allauth_socialapp_sites_site_id_26af3e5b_fk_django_site_id FOREIGN KEY (site_id) REFERENCES public.django_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: allauth_socialtoken allauth_socialtoken_account_id_188497ae_fk_allauth_s; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialtoken
    ADD CONSTRAINT allauth_socialtoken_account_id_188497ae_fk_allauth_s FOREIGN KEY (account_id) REFERENCES public.allauth_socialaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: allauth_socialtoken allauth_socialtoken_app_id_f34fc476_fk_allauth_socialapp_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.allauth_socialtoken
    ADD CONSTRAINT allauth_socialtoken_app_id_f34fc476_fk_allauth_socialapp_id FOREIGN KEY (app_id) REFERENCES public.allauth_socialapp(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authtoken_token authtoken_token_user_id_35299eff_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.authtoken_token
    ADD CONSTRAINT authtoken_token_user_id_35299eff_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: banner_bannerdata banner_bannerdata_banner_data_id_4e86c5fe_fk_banner_banner_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerdata
    ADD CONSTRAINT banner_bannerdata_banner_data_id_4e86c5fe_fk_banner_banner_id FOREIGN KEY (banner_data_id) REFERENCES public.banner_banner(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: banner_bannerdata banner_bannerdata_slot_id_17c528d7_fk_banner_bannerposition_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerdata
    ADD CONSTRAINT banner_bannerdata_slot_id_17c528d7_fk_banner_bannerposition_id FOREIGN KEY (slot_id) REFERENCES public.banner_bannerposition(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: banner_bannerposition banner_bannerpositio_bannerslot_id_91f6b39d_fk_banner_ba; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerposition
    ADD CONSTRAINT banner_bannerpositio_bannerslot_id_91f6b39d_fk_banner_ba FOREIGN KEY (bannerslot_id) REFERENCES public.banner_bannerslot(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: banner_bannerposition banner_bannerposition_page_id_64226b4c_fk_banner_page_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerposition
    ADD CONSTRAINT banner_bannerposition_page_id_64226b4c_fk_banner_page_id FOREIGN KEY (page_id) REFERENCES public.banner_page(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: banner_bannerslot banner_bannerslot_page_id_2c9e527c_fk_banner_page_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.banner_bannerslot
    ADD CONSTRAINT banner_bannerslot_page_id_2c9e527c_fk_banner_page_id FOREIGN KEY (page_id) REFERENCES public.banner_page(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: brand_brand brand_brand_brand_parent_id_660df75f_fk_brand_brand_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_brand
    ADD CONSTRAINT brand_brand_brand_parent_id_660df75f_fk_brand_brand_id FOREIGN KEY (brand_parent_id) REFERENCES public.brand_brand(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: brand_branddata brand_branddata_brand_data_id_880a904d_fk_brand_brand_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_branddata
    ADD CONSTRAINT brand_branddata_brand_data_id_880a904d_fk_brand_brand_id FOREIGN KEY (brand_data_id) REFERENCES public.brand_brand(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: brand_branddata brand_branddata_slot_id_6e3f43c3_fk_brand_brandposition_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_branddata
    ADD CONSTRAINT brand_branddata_slot_id_6e3f43c3_fk_brand_brandposition_id FOREIGN KEY (slot_id) REFERENCES public.brand_brandposition(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: brand_vendor brand_vendor_city_id_c411df76_fk_addresses_city_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_vendor
    ADD CONSTRAINT brand_vendor_city_id_c411df76_fk_addresses_city_id FOREIGN KEY (city_id) REFERENCES public.addresses_city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: brand_vendor brand_vendor_state_id_47e1bd64_fk_addresses_state_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.brand_vendor
    ADD CONSTRAINT brand_vendor_state_id_47e1bd64_fk_addresses_state_id FOREIGN KEY (state_id) REFERENCES public.addresses_state(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: categories_category categories_category_category_parent_id_deb82704_fk_categorie; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_category
    ADD CONSTRAINT categories_category_category_parent_id_deb82704_fk_categorie FOREIGN KEY (category_parent_id) REFERENCES public.categories_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: categories_categorydata categories_categoryd_category_data_id_f5565bf2_fk_categorie; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_categorydata
    ADD CONSTRAINT categories_categoryd_category_data_id_f5565bf2_fk_categorie FOREIGN KEY (category_data_id) REFERENCES public.categories_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: categories_categorydata categories_categoryd_category_pos_id_df2f1117_fk_categorie; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.categories_categorydata
    ADD CONSTRAINT categories_categoryd_category_pos_id_df2f1117_fk_categorie FOREIGN KEY (category_pos_id) REFERENCES public.categories_categoryposation(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_brandnote gram_to_brand_brandn_grn_order_id_976650a3_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_brandnote
    ADD CONSTRAINT gram_to_brand_brandn_grn_order_id_976650a3_fk_gram_to_b FOREIGN KEY (grn_order_id) REFERENCES public.gram_to_brand_grnorder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_brandnote gram_to_brand_brandn_last_modified_by_id_c7ed17b3_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_brandnote
    ADD CONSTRAINT gram_to_brand_brandn_last_modified_by_id_c7ed17b3_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_brandnote gram_to_brand_brandn_order_id_b3511b90_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_brandnote
    ADD CONSTRAINT gram_to_brand_brandn_order_id_b3511b90_fk_gram_to_b FOREIGN KEY (order_id) REFERENCES public.gram_to_brand_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_brand_id_31d2b48d_fk_brand_brand_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_brand_id_31d2b48d_fk_brand_brand_id FOREIGN KEY (brand_id) REFERENCES public.brand_brand(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_gf_billing_address_i_11a93f68_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_gf_billing_address_i_11a93f68_fk_addresses FOREIGN KEY (gf_billing_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_gf_shipping_address__775b7e1d_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_gf_shipping_address__775b7e1d_fk_addresses FOREIGN KEY (gf_shipping_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_last_modified_by_id_f5d9393f_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_last_modified_by_id_f5d9393f_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_po_message_id_efd7dc51_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_po_message_id_efd7dc51_fk_gram_to_b FOREIGN KEY (po_message_id) REFERENCES public.gram_to_brand_po_message(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_po_raised_by_id_6c46c9e1_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_po_raised_by_id_6c46c9e1_fk_accounts_user_id FOREIGN KEY (po_raised_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_shop_id_eec83ebf_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_shop_id_eec83ebf_fk_shops_shop_id FOREIGN KEY (shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_supplier_name_id_f692b789_fk_brand_vendor_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_supplier_name_id_f692b789_fk_brand_vendor_id FOREIGN KEY (supplier_name_id) REFERENCES public.brand_vendor(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cart gram_to_brand_cart_supplier_state_id_bbd262da_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cart
    ADD CONSTRAINT gram_to_brand_cart_supplier_state_id_bbd262da_fk_addresses FOREIGN KEY (supplier_state_id) REFERENCES public.addresses_state(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cartproductmapping gram_to_brand_cartpr_cart_id_e33c9b36_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cartproductmapping
    ADD CONSTRAINT gram_to_brand_cartpr_cart_id_e33c9b36_fk_gram_to_b FOREIGN KEY (cart_id) REFERENCES public.gram_to_brand_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_cartproductmapping gram_to_brand_cartpr_cart_product_id_44cedeed_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_cartproductmapping
    ADD CONSTRAINT gram_to_brand_cartpr_cart_product_id_44cedeed_fk_products_ FOREIGN KEY (cart_product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproducthistory gram_to_brand_grnord_grn_order_id_08171666_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory
    ADD CONSTRAINT gram_to_brand_grnord_grn_order_id_08171666_fk_gram_to_b FOREIGN KEY (grn_order_id) REFERENCES public.gram_to_brand_grnorder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproductmapping gram_to_brand_grnord_grn_order_id_b06c17ed_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproductmapping
    ADD CONSTRAINT gram_to_brand_grnord_grn_order_id_b06c17ed_fk_gram_to_b FOREIGN KEY (grn_order_id) REFERENCES public.gram_to_brand_grnorder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorder gram_to_brand_grnord_last_modified_by_id_4f77c029_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorder
    ADD CONSTRAINT gram_to_brand_grnord_last_modified_by_id_4f77c029_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproducthistory gram_to_brand_grnord_last_modified_by_id_ccd70c3f_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory
    ADD CONSTRAINT gram_to_brand_grnord_last_modified_by_id_ccd70c3f_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproductmapping gram_to_brand_grnord_last_modified_by_id_fea4295a_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproductmapping
    ADD CONSTRAINT gram_to_brand_grnord_last_modified_by_id_fea4295a_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproducthistory gram_to_brand_grnord_order_id_38bc0890_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory
    ADD CONSTRAINT gram_to_brand_grnord_order_id_38bc0890_fk_gram_to_b FOREIGN KEY (order_id) REFERENCES public.gram_to_brand_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorder gram_to_brand_grnord_order_id_a346e896_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorder
    ADD CONSTRAINT gram_to_brand_grnord_order_id_a346e896_fk_gram_to_b FOREIGN KEY (order_id) REFERENCES public.gram_to_brand_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorder gram_to_brand_grnord_order_item_id_1ce00752_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorder
    ADD CONSTRAINT gram_to_brand_grnord_order_item_id_1ce00752_fk_gram_to_b FOREIGN KEY (order_item_id) REFERENCES public.gram_to_brand_orderitem(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproducthistory gram_to_brand_grnord_order_item_id_ac417f8f_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory
    ADD CONSTRAINT gram_to_brand_grnord_order_item_id_ac417f8f_fk_gram_to_b FOREIGN KEY (order_item_id) REFERENCES public.gram_to_brand_orderitem(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproductmapping gram_to_brand_grnord_product_id_361def72_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproductmapping
    ADD CONSTRAINT gram_to_brand_grnord_product_id_361def72_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_grnorderproducthistory gram_to_brand_grnord_product_id_f6f5af96_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_grnorderproducthistory
    ADD CONSTRAINT gram_to_brand_grnord_product_id_f6f5af96_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_billing_address_id_9d176a19_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_billing_address_id_9d176a19_fk_addresses FOREIGN KEY (billing_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_last_modified_by_id_3ee5370c_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_last_modified_by_id_3ee5370c_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_ordered_by_id_3a6b0324_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_ordered_by_id_3a6b0324_fk_accounts_user_id FOREIGN KEY (ordered_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_ordered_cart_id_7c60e36b_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_ordered_cart_id_7c60e36b_fk_gram_to_b FOREIGN KEY (ordered_cart_id) REFERENCES public.gram_to_brand_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_received_by_id_fd0a8f7e_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_received_by_id_fd0a8f7e_fk_accounts_user_id FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_shipping_address_id_9f9d66c0_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_shipping_address_id_9f9d66c0_fk_addresses FOREIGN KEY (shipping_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_order gram_to_brand_order_shop_id_0dcee062_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_order
    ADD CONSTRAINT gram_to_brand_order_shop_id_0dcee062_fk_shops_shop_id FOREIGN KEY (shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderedproductreserved gram_to_brand_ordere_cart_id_7c851e22_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderedproductreserved
    ADD CONSTRAINT gram_to_brand_ordere_cart_id_7c851e22_fk_retailer_ FOREIGN KEY (cart_id) REFERENCES public.retailer_to_gram_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderedproductreserved gram_to_brand_ordere_order_product_reserv_7b7d2f5a_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderedproductreserved
    ADD CONSTRAINT gram_to_brand_ordere_order_product_reserv_7b7d2f5a_fk_gram_to_b FOREIGN KEY (order_product_reserved_id) REFERENCES public.gram_to_brand_grnorderproductmapping(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderedproductreserved gram_to_brand_ordere_product_id_3750ee6c_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderedproductreserved
    ADD CONSTRAINT gram_to_brand_ordere_product_id_3750ee6c_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_billing_address_id_a8520355_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_billing_address_id_a8520355_fk_addresses FOREIGN KEY (billing_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_buyer_shop_id_bfea710e_fk_shops_sho; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_buyer_shop_id_bfea710e_fk_shops_sho FOREIGN KEY (buyer_shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_last_modified_by_id_d57f7154_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_last_modified_by_id_d57f7154_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_ordered_by_id_ac4a43bc_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_ordered_by_id_ac4a43bc_fk_accounts_ FOREIGN KEY (ordered_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_ordered_cart_id_eb53e26e_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_ordered_cart_id_eb53e26e_fk_gram_to_b FOREIGN KEY (ordered_cart_id) REFERENCES public.gram_to_brand_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_received_by_id_8fdc3115_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_received_by_id_8fdc3115_fk_accounts_ FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_seller_shop_id_2c321d21_fk_shops_sho; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_seller_shop_id_2c321d21_fk_shops_sho FOREIGN KEY (seller_shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderhistory gram_to_brand_orderh_shipping_address_id_096ca4ec_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderhistory
    ADD CONSTRAINT gram_to_brand_orderh_shipping_address_id_096ca4ec_fk_addresses FOREIGN KEY (shipping_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderitem gram_to_brand_orderi_last_modified_by_id_b4f9089f_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderitem
    ADD CONSTRAINT gram_to_brand_orderi_last_modified_by_id_b4f9089f_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderitem gram_to_brand_orderi_order_id_49494a20_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderitem
    ADD CONSTRAINT gram_to_brand_orderi_order_id_49494a20_fk_gram_to_b FOREIGN KEY (order_id) REFERENCES public.gram_to_brand_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_orderitem gram_to_brand_orderi_ordered_product_id_44c5b4a8_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_orderitem
    ADD CONSTRAINT gram_to_brand_orderi_ordered_product_id_44c5b4a8_fk_products_ FOREIGN KEY (ordered_product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_picklist gram_to_brand_pickli_cart_id_8b2c917c_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklist
    ADD CONSTRAINT gram_to_brand_pickli_cart_id_8b2c917c_fk_retailer_ FOREIGN KEY (cart_id) REFERENCES public.retailer_to_gram_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_picklistitems gram_to_brand_pickli_grn_order_id_9a26fdff_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklistitems
    ADD CONSTRAINT gram_to_brand_pickli_grn_order_id_9a26fdff_fk_gram_to_b FOREIGN KEY (grn_order_id) REFERENCES public.gram_to_brand_grnorder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_picklist gram_to_brand_pickli_order_id_61071bf2_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklist
    ADD CONSTRAINT gram_to_brand_pickli_order_id_61071bf2_fk_retailer_ FOREIGN KEY (order_id) REFERENCES public.retailer_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_picklistitems gram_to_brand_pickli_pick_list_id_2627ea46_fk_gram_to_b; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklistitems
    ADD CONSTRAINT gram_to_brand_pickli_pick_list_id_2627ea46_fk_gram_to_b FOREIGN KEY (pick_list_id) REFERENCES public.gram_to_brand_picklist(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_picklistitems gram_to_brand_pickli_product_id_1d553e21_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_picklistitems
    ADD CONSTRAINT gram_to_brand_pickli_product_id_1d553e21_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: gram_to_brand_po_message gram_to_brand_po_mes_created_by_id_f4866384_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.gram_to_brand_po_message
    ADD CONSTRAINT gram_to_brand_po_mes_created_by_id_f4866384_fk_accounts_ FOREIGN KEY (created_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_product products_product_product_brand_id_1d698d6e_fk_brand_brand_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_product
    ADD CONSTRAINT products_product_product_brand_id_1d698d6e_fk_brand_brand_id FOREIGN KEY (product_brand_id) REFERENCES public.brand_brand(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productcategory products_productcate_category_id_89ea68e5_fk_categorie; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategory
    ADD CONSTRAINT products_productcate_category_id_89ea68e5_fk_categorie FOREIGN KEY (category_id) REFERENCES public.categories_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productcategoryhistory products_productcate_category_id_c4fb4b4b_fk_categorie; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategoryhistory
    ADD CONSTRAINT products_productcate_category_id_c4fb4b4b_fk_categorie FOREIGN KEY (category_id) REFERENCES public.categories_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productcategoryhistory products_productcate_product_id_090e0c13_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategoryhistory
    ADD CONSTRAINT products_productcate_product_id_090e0c13_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productcategory products_productcate_product_id_acd5dd19_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productcategory
    ADD CONSTRAINT products_productcate_product_id_acd5dd19_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productimage products_productimag_product_id_e747596a_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productimage
    ADD CONSTRAINT products_productimag_product_id_e747596a_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productopti_fragrance_id_c8c243de_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productopti_fragrance_id_c8c243de_fk_products_ FOREIGN KEY (fragrance_id) REFERENCES public.products_fragrance(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productopti_package_size_id_e309b1aa_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productopti_package_size_id_e309b1aa_fk_products_ FOREIGN KEY (package_size_id) REFERENCES public.products_packagesize(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productopti_product_id_6dc2057d_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productopti_product_id_6dc2057d_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productoption_color_id_e61e2def_fk_products_color_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productoption_color_id_e61e2def_fk_products_color_id FOREIGN KEY (color_id) REFERENCES public.products_color(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productoption_flavor_id_4e6120f5_fk_products_flavor_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productoption_flavor_id_4e6120f5_fk_products_flavor_id FOREIGN KEY (flavor_id) REFERENCES public.products_flavor(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productoption_size_id_93ade64f_fk_products_size_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productoption_size_id_93ade64f_fk_products_size_id FOREIGN KEY (size_id) REFERENCES public.products_size(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productoption products_productoption_weight_id_2bf64ad6_fk_products_weight_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productoption
    ADD CONSTRAINT products_productoption_weight_id_2bf64ad6_fk_products_weight_id FOREIGN KEY (weight_id) REFERENCES public.products_weight(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productpricecsv products_productpric_country_id_29c73281_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productpricecsv
    ADD CONSTRAINT products_productpric_country_id_29c73281_fk_addresses FOREIGN KEY (country_id) REFERENCES public.addresses_country(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productprice products_productpric_product_id_efef3000_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productprice
    ADD CONSTRAINT products_productpric_product_id_efef3000_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productpricecsv products_productpric_states_id_8de350d1_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productpricecsv
    ADD CONSTRAINT products_productpric_states_id_8de350d1_fk_addresses FOREIGN KEY (states_id) REFERENCES public.addresses_state(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productprice products_productprice_area_id_f942f99b_fk_addresses_area_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productprice
    ADD CONSTRAINT products_productprice_area_id_f942f99b_fk_addresses_area_id FOREIGN KEY (area_id) REFERENCES public.addresses_area(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productprice products_productprice_city_id_86b4ddd8_fk_addresses_city_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productprice
    ADD CONSTRAINT products_productprice_city_id_86b4ddd8_fk_addresses_city_id FOREIGN KEY (city_id) REFERENCES public.addresses_city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productprice products_productprice_shop_id_2ec945ae_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productprice
    ADD CONSTRAINT products_productprice_shop_id_2ec945ae_fk_shops_shop_id FOREIGN KEY (shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productpricecsv products_productpricecsv_area_id_3cc79290_fk_addresses_area_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productpricecsv
    ADD CONSTRAINT products_productpricecsv_area_id_3cc79290_fk_addresses_area_id FOREIGN KEY (area_id) REFERENCES public.addresses_area(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productpricecsv products_productpricecsv_city_id_987b5623_fk_addresses_city_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productpricecsv
    ADD CONSTRAINT products_productpricecsv_city_id_987b5623_fk_addresses_city_id FOREIGN KEY (city_id) REFERENCES public.addresses_city(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_producttaxmapping products_producttaxm_product_id_9d39623c_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_producttaxmapping
    ADD CONSTRAINT products_producttaxm_product_id_9d39623c_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_producttaxmapping products_producttaxmapping_tax_id_18a14597_fk_products_tax_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_producttaxmapping
    ADD CONSTRAINT products_producttaxmapping_tax_id_18a14597_fk_products_tax_id FOREIGN KEY (tax_id) REFERENCES public.products_tax(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productvendormapping products_productvend_product_id_4831243c_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productvendormapping
    ADD CONSTRAINT products_productvend_product_id_4831243c_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: products_productvendormapping products_productvend_vendor_id_d9bc27fc_fk_brand_ven; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.products_productvendormapping
    ADD CONSTRAINT products_productvend_vendor_id_d9bc27fc_fk_brand_ven FOREIGN KEY (vendor_id) REFERENCES public.brand_vendor(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_cartproductmapping retailer_to_gram_car_cart_id_fe0d96a5_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cartproductmapping
    ADD CONSTRAINT retailer_to_gram_car_cart_id_fe0d96a5_fk_retailer_ FOREIGN KEY (cart_id) REFERENCES public.retailer_to_gram_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_cartproductmapping retailer_to_gram_car_cart_product_id_69584057_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cartproductmapping
    ADD CONSTRAINT retailer_to_gram_car_cart_product_id_69584057_fk_products_ FOREIGN KEY (cart_product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_cart retailer_to_gram_car_last_modified_by_id_1ca90b12_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_cart
    ADD CONSTRAINT retailer_to_gram_car_last_modified_by_id_1ca90b12_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_customercare retailer_to_gram_cus_order_id_id_ce80023f_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_customercare
    ADD CONSTRAINT retailer_to_gram_cus_order_id_id_ce80023f_fk_retailer_ FOREIGN KEY (order_id_id) REFERENCES public.retailer_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_note retailer_to_gram_not_last_modified_by_id_12493eb0_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_note
    ADD CONSTRAINT retailer_to_gram_not_last_modified_by_id_12493eb0_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_note retailer_to_gram_not_order_id_92a72968_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_note
    ADD CONSTRAINT retailer_to_gram_not_order_id_92a72968_fk_retailer_ FOREIGN KEY (order_id) REFERENCES public.retailer_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_note retailer_to_gram_not_ordered_product_id_3ab64437_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_note
    ADD CONSTRAINT retailer_to_gram_not_ordered_product_id_3ab64437_fk_retailer_ FOREIGN KEY (ordered_product_id) REFERENCES public.retailer_to_gram_orderedproduct(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_ord_billing_address_id_2a9ce80d_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_ord_billing_address_id_2a9ce80d_fk_addresses FOREIGN KEY (billing_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproduct retailer_to_gram_ord_last_modified_by_id_86a72784_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproduct
    ADD CONSTRAINT retailer_to_gram_ord_last_modified_by_id_86a72784_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproductmapping retailer_to_gram_ord_last_modified_by_id_c14095fe_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproductmapping
    ADD CONSTRAINT retailer_to_gram_ord_last_modified_by_id_c14095fe_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_ord_last_modified_by_id_e6c3d296_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_ord_last_modified_by_id_e6c3d296_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproduct retailer_to_gram_ord_order_id_9ebac3d0_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproduct
    ADD CONSTRAINT retailer_to_gram_ord_order_id_9ebac3d0_fk_retailer_ FOREIGN KEY (order_id) REFERENCES public.retailer_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_ord_ordered_by_id_5f029772_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_ord_ordered_by_id_5f029772_fk_accounts_ FOREIGN KEY (ordered_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_ord_ordered_cart_id_0993e56e_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_ord_ordered_cart_id_0993e56e_fk_retailer_ FOREIGN KEY (ordered_cart_id) REFERENCES public.retailer_to_gram_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproductmapping retailer_to_gram_ord_ordered_product_id_b4829f7d_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproductmapping
    ADD CONSTRAINT retailer_to_gram_ord_ordered_product_id_b4829f7d_fk_retailer_ FOREIGN KEY (ordered_product_id) REFERENCES public.retailer_to_gram_orderedproduct(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproductmapping retailer_to_gram_ord_product_id_ed795395_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproductmapping
    ADD CONSTRAINT retailer_to_gram_ord_product_id_ed795395_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproduct retailer_to_gram_ord_received_by_id_41ae19b2_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproduct
    ADD CONSTRAINT retailer_to_gram_ord_received_by_id_41ae19b2_fk_accounts_ FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_ord_received_by_id_e1850936_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_ord_received_by_id_e1850936_fk_accounts_ FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_orderedproduct retailer_to_gram_ord_shipped_by_id_415524e6_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_orderedproduct
    ADD CONSTRAINT retailer_to_gram_ord_shipped_by_id_415524e6_fk_accounts_ FOREIGN KEY (shipped_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_ord_shipping_address_id_4f8d3b5a_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_ord_shipping_address_id_4f8d3b5a_fk_addresses FOREIGN KEY (shipping_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_order_buyer_shop_id_720a6f53_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_order_buyer_shop_id_720a6f53_fk_shops_shop_id FOREIGN KEY (buyer_shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_order retailer_to_gram_order_seller_shop_id_739a7026_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_order
    ADD CONSTRAINT retailer_to_gram_order_seller_shop_id_739a7026_fk_shops_shop_id FOREIGN KEY (seller_shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_gram_payment retailer_to_gram_pay_order_id_id_a3f9d00b_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_gram_payment
    ADD CONSTRAINT retailer_to_gram_pay_order_id_id_a3f9d00b_fk_retailer_ FOREIGN KEY (order_id_id) REFERENCES public.retailer_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_cart retailer_to_sp_cart_last_modified_by_id_2464780e_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cart
    ADD CONSTRAINT retailer_to_sp_cart_last_modified_by_id_2464780e_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_cartproductmapping retailer_to_sp_cartp_cart_id_35aa1297_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cartproductmapping
    ADD CONSTRAINT retailer_to_sp_cartp_cart_id_35aa1297_fk_retailer_ FOREIGN KEY (cart_id) REFERENCES public.retailer_to_sp_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_cartproductmapping retailer_to_sp_cartp_cart_product_id_b52f6ff1_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_cartproductmapping
    ADD CONSTRAINT retailer_to_sp_cartp_cart_product_id_b52f6ff1_fk_products_ FOREIGN KEY (cart_product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_customercare retailer_to_sp_custo_order_id_id_3c80587a_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_customercare
    ADD CONSTRAINT retailer_to_sp_custo_order_id_id_3c80587a_fk_retailer_ FOREIGN KEY (order_id_id) REFERENCES public.retailer_to_sp_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_note retailer_to_sp_note_last_modified_by_id_0fc126c4_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_note
    ADD CONSTRAINT retailer_to_sp_note_last_modified_by_id_0fc126c4_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_note retailer_to_sp_note_order_id_2ea61fcd_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_note
    ADD CONSTRAINT retailer_to_sp_note_order_id_2ea61fcd_fk_retailer_ FOREIGN KEY (order_id) REFERENCES public.retailer_to_sp_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_note retailer_to_sp_note_ordered_product_id_c6c698ba_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_note
    ADD CONSTRAINT retailer_to_sp_note_ordered_product_id_c6c698ba_fk_retailer_ FOREIGN KEY (ordered_product_id) REFERENCES public.retailer_to_sp_orderedproduct(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_billing_address_id_5361f86b_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_billing_address_id_5361f86b_fk_addresses FOREIGN KEY (billing_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_buyer_shop_id_cdd19a74_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_buyer_shop_id_cdd19a74_fk_shops_shop_id FOREIGN KEY (buyer_shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_last_modified_by_id_50939d56_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_last_modified_by_id_50939d56_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproduct retailer_to_sp_order_last_modified_by_id_65925327_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproduct
    ADD CONSTRAINT retailer_to_sp_order_last_modified_by_id_65925327_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproductmapping retailer_to_sp_order_last_modified_by_id_73bebc82_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproductmapping
    ADD CONSTRAINT retailer_to_sp_order_last_modified_by_id_73bebc82_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproduct retailer_to_sp_order_order_id_532bc99c_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproduct
    ADD CONSTRAINT retailer_to_sp_order_order_id_532bc99c_fk_retailer_ FOREIGN KEY (order_id) REFERENCES public.retailer_to_sp_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_ordered_by_id_366d32bc_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_ordered_by_id_366d32bc_fk_accounts_user_id FOREIGN KEY (ordered_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_ordered_cart_id_c9dc11fa_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_ordered_cart_id_c9dc11fa_fk_retailer_ FOREIGN KEY (ordered_cart_id) REFERENCES public.retailer_to_sp_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproductmapping retailer_to_sp_order_ordered_product_id_a597c9db_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproductmapping
    ADD CONSTRAINT retailer_to_sp_order_ordered_product_id_a597c9db_fk_retailer_ FOREIGN KEY (ordered_product_id) REFERENCES public.retailer_to_sp_orderedproduct(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproductmapping retailer_to_sp_order_product_id_54dd513b_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproductmapping
    ADD CONSTRAINT retailer_to_sp_order_product_id_54dd513b_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_received_by_id_27c7bb7d_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_received_by_id_27c7bb7d_fk_accounts_ FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproduct retailer_to_sp_order_received_by_id_8bd3c1c4_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproduct
    ADD CONSTRAINT retailer_to_sp_order_received_by_id_8bd3c1c4_fk_accounts_ FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_seller_shop_id_0c71a300_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_seller_shop_id_0c71a300_fk_shops_shop_id FOREIGN KEY (seller_shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_orderedproduct retailer_to_sp_order_shipped_by_id_f014d527_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_orderedproduct
    ADD CONSTRAINT retailer_to_sp_order_shipped_by_id_f014d527_fk_accounts_ FOREIGN KEY (shipped_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_order retailer_to_sp_order_shipping_address_id_aa615dea_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_order
    ADD CONSTRAINT retailer_to_sp_order_shipping_address_id_aa615dea_fk_addresses FOREIGN KEY (shipping_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: retailer_to_sp_payment retailer_to_sp_payme_order_id_id_206e64b0_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.retailer_to_sp_payment
    ADD CONSTRAINT retailer_to_sp_payme_order_id_id_206e64b0_fk_retailer_ FOREIGN KEY (order_id_id) REFERENCES public.retailer_to_sp_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_parentretailermapping shops_parentretailer_retailer_id_48f7b6d0_fk_shops_sho; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_parentretailermapping
    ADD CONSTRAINT shops_parentretailer_retailer_id_48f7b6d0_fk_shops_sho FOREIGN KEY (retailer_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_parentretailermapping shops_parentretailermapping_parent_id_385afda4_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_parentretailermapping
    ADD CONSTRAINT shops_parentretailermapping_parent_id_385afda4_fk_shops_shop_id FOREIGN KEY (parent_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shop_related_users shops_shop_related_users_shop_id_3601acae_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop_related_users
    ADD CONSTRAINT shops_shop_related_users_shop_id_3601acae_fk_shops_shop_id FOREIGN KEY (shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shop_related_users shops_shop_related_users_user_id_ecee493d_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop_related_users
    ADD CONSTRAINT shops_shop_related_users_user_id_ecee493d_fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shop shops_shop_shop_owner_id_3a01cb19_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop
    ADD CONSTRAINT shops_shop_shop_owner_id_3a01cb19_fk_accounts_user_id FOREIGN KEY (shop_owner_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shop shops_shop_shop_type_id_8f5bca08_fk_shops_shoptype_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shop
    ADD CONSTRAINT shops_shop_shop_type_id_8f5bca08_fk_shops_shoptype_id FOREIGN KEY (shop_type_id) REFERENCES public.shops_shoptype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shopdocument shops_shopdocument_shop_name_id_b1644942_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shopdocument
    ADD CONSTRAINT shops_shopdocument_shop_name_id_b1644942_fk_shops_shop_id FOREIGN KEY (shop_name_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shopphoto shops_shopphoto_shop_name_id_d9efdb28_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shopphoto
    ADD CONSTRAINT shops_shopphoto_shop_name_id_d9efdb28_fk_shops_shop_id FOREIGN KEY (shop_name_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: shops_shoptype shops_shoptype_shop_sub_type_id_c9d3a779_fk_shops_ret; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.shops_shoptype
    ADD CONSTRAINT shops_shoptype_shop_sub_type_id_c9d3a779_fk_shops_ret FOREIGN KEY (shop_sub_type_id) REFERENCES public.shops_retailertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_cart sp_to_gram_cart_last_modified_by_id_39fdf725_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cart
    ADD CONSTRAINT sp_to_gram_cart_last_modified_by_id_39fdf725_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_cart sp_to_gram_cart_po_raised_by_id_fca43b07_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cart
    ADD CONSTRAINT sp_to_gram_cart_po_raised_by_id_fca43b07_fk_accounts_user_id FOREIGN KEY (po_raised_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_cart sp_to_gram_cart_shop_id_e8ed569c_fk_shops_shop_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cart
    ADD CONSTRAINT sp_to_gram_cart_shop_id_e8ed569c_fk_shops_shop_id FOREIGN KEY (shop_id) REFERENCES public.shops_shop(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_cartproductmapping sp_to_gram_cartprodu_cart_id_b5f0d261_fk_sp_to_gra; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cartproductmapping
    ADD CONSTRAINT sp_to_gram_cartprodu_cart_id_b5f0d261_fk_sp_to_gra FOREIGN KEY (cart_id) REFERENCES public.sp_to_gram_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_cartproductmapping sp_to_gram_cartprodu_cart_product_id_385ec226_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_cartproductmapping
    ADD CONSTRAINT sp_to_gram_cartprodu_cart_product_id_385ec226_fk_products_ FOREIGN KEY (cart_product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_order sp_to_gram_order_billing_address_id_c2ec935f_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_billing_address_id_c2ec935f_fk_addresses FOREIGN KEY (billing_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_order sp_to_gram_order_last_modified_by_id_e340f48f_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_last_modified_by_id_e340f48f_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_order sp_to_gram_order_ordered_by_id_bb437ba6_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_ordered_by_id_bb437ba6_fk_accounts_user_id FOREIGN KEY (ordered_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_order sp_to_gram_order_ordered_cart_id_deab1bca_fk_sp_to_gram_cart_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_ordered_cart_id_deab1bca_fk_sp_to_gram_cart_id FOREIGN KEY (ordered_cart_id) REFERENCES public.sp_to_gram_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_order sp_to_gram_order_received_by_id_25eec96e_fk_accounts_user_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_received_by_id_25eec96e_fk_accounts_user_id FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_order sp_to_gram_order_shipping_address_id_87126904_fk_addresses; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_order
    ADD CONSTRAINT sp_to_gram_order_shipping_address_id_87126904_fk_addresses FOREIGN KEY (shipping_address_id) REFERENCES public.addresses_address(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproductreserved sp_to_gram_orderedpr_cart_id_3a10e771_fk_retailer_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductreserved
    ADD CONSTRAINT sp_to_gram_orderedpr_cart_id_3a10e771_fk_retailer_ FOREIGN KEY (cart_id) REFERENCES public.retailer_to_sp_cart(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproduct sp_to_gram_orderedpr_last_modified_by_id_1db1474c_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproduct
    ADD CONSTRAINT sp_to_gram_orderedpr_last_modified_by_id_1db1474c_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproductmapping sp_to_gram_orderedpr_last_modified_by_id_fc82ae35_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductmapping
    ADD CONSTRAINT sp_to_gram_orderedpr_last_modified_by_id_fc82ae35_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproduct sp_to_gram_orderedpr_order_id_836db601_fk_sp_to_gra; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproduct
    ADD CONSTRAINT sp_to_gram_orderedpr_order_id_836db601_fk_sp_to_gra FOREIGN KEY (order_id) REFERENCES public.sp_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproductreserved sp_to_gram_orderedpr_order_product_reserv_6a000eee_fk_sp_to_gra; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductreserved
    ADD CONSTRAINT sp_to_gram_orderedpr_order_product_reserv_6a000eee_fk_sp_to_gra FOREIGN KEY (order_product_reserved_id) REFERENCES public.sp_to_gram_orderedproductmapping(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproductmapping sp_to_gram_orderedpr_ordered_product_id_2ecd7ed2_fk_sp_to_gra; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductmapping
    ADD CONSTRAINT sp_to_gram_orderedpr_ordered_product_id_2ecd7ed2_fk_sp_to_gra FOREIGN KEY (ordered_product_id) REFERENCES public.sp_to_gram_orderedproduct(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproductreserved sp_to_gram_orderedpr_product_id_b05783cb_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductreserved
    ADD CONSTRAINT sp_to_gram_orderedpr_product_id_b05783cb_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproductmapping sp_to_gram_orderedpr_product_id_b716f00e_fk_products_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproductmapping
    ADD CONSTRAINT sp_to_gram_orderedpr_product_id_b716f00e_fk_products_ FOREIGN KEY (product_id) REFERENCES public.products_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproduct sp_to_gram_orderedpr_received_by_id_57a2d639_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproduct
    ADD CONSTRAINT sp_to_gram_orderedpr_received_by_id_57a2d639_fk_accounts_ FOREIGN KEY (received_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_orderedproduct sp_to_gram_orderedpr_shipped_by_id_e9504c74_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_orderedproduct
    ADD CONSTRAINT sp_to_gram_orderedpr_shipped_by_id_e9504c74_fk_accounts_ FOREIGN KEY (shipped_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_spnote sp_to_gram_spnote_grn_order_id_ac835aa9_fk_sp_to_gra; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_spnote
    ADD CONSTRAINT sp_to_gram_spnote_grn_order_id_ac835aa9_fk_sp_to_gra FOREIGN KEY (grn_order_id) REFERENCES public.sp_to_gram_orderedproduct(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_spnote sp_to_gram_spnote_last_modified_by_id_a6400570_fk_accounts_; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_spnote
    ADD CONSTRAINT sp_to_gram_spnote_last_modified_by_id_a6400570_fk_accounts_ FOREIGN KEY (last_modified_by_id) REFERENCES public.accounts_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: sp_to_gram_spnote sp_to_gram_spnote_order_id_7fb63660_fk_sp_to_gram_order_id; Type: FK CONSTRAINT; Schema: public; Owner: gramfac18
--

ALTER TABLE ONLY public.sp_to_gram_spnote
    ADD CONSTRAINT sp_to_gram_spnote_order_id_7fb63660_fk_sp_to_gram_order_id FOREIGN KEY (order_id) REFERENCES public.sp_to_gram_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: gramfac18
--

REVOKE ALL ON SCHEMA public FROM rdsadmin;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO gramfac18;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

