global_defs {
    router_id ${HOSTNAME}
    script_user root
    enable_script_security
}

vrrp_script chk_pihole {
    script "/scripts/check_health.sh"
    interval 3  # check every 3 seconds
    timeout 2   # timeout after 2 seconds
    weight -20  # reduce priority by 20 if check fails
    fall 3      # require 3 failures for KO
    rise 2      # require 2 successes for OK
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
    
    # Optional: notify scripts can be added here
    # notify "/scripts/notify.sh"
}
