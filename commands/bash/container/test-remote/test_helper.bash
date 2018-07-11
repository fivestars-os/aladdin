function wait_condition {
    local condition="$1"
    local max_time="$2"
    total_sleep=0
    while ! eval "$condition"; do
        sleep 10
        total_sleep=$(($total_sleep+10))
        if [[ $total_sleep -gt $max_time ]]; then
            return 1
        fi
    done
    return 0
}

function get_elb {
    local service="$1"
    kubectl get svc "$service" -o json | jq -r .status.loadBalancer.ingress[0].hostname
}

function get_cname_value {
    local service_name="$1"
    local hosted_zone="$2".
    hosted_zone_id=$(aws route53 list-hosted-zones-by-name | jq -r --arg hz "$hosted_zone" '.HostedZones[] | select (.Name == $hz).Id')
    aws route53 list-resource-record-sets --hosted-zone-id "$hosted_zone_id" | jq -r --arg name "$service_name.$hosted_zone" '.ResourceRecordSets[] | select (.Name==$name).ResourceRecords[0].Value'
}
