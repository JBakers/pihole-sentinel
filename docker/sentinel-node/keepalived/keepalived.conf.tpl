global_defs {
    router_id ${HOSTNAME}
    script_user root
    enable_script_security
}

vrrp_script chk_pihole {
    script "/scripts/check_health.sh"
    interval 3
    timeout 2
    weight -20
    fall 3
    rise 2
}

vrrp_instance PIHOLE_HA {
    state ${KEEPALIVED_STATE}
    interface ${KEEPALIVED_INTERFACE}
    virtual_router_id ${KEEPALIVED_ROUTER_ID}
    priority ${KEEPALIVED_PRIORITY}
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass ${KEEPALIVED_AUTH_PASS}
    }

    virtual_ipaddress {
        ${VIP_IP}/24
    }

    track_script {
        chk_pihole
    }

    notify "/scripts/notify.sh"
}
