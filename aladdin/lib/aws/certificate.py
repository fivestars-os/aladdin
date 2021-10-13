"""
Helpers function to get/create certificates the way we want
"""
import logging
import re
from hashlib import md5

from aladdin.lib.aws.dns_mapping import create_hostedzone, fill_dns_dict, get_hostedzone


def search_certificate_arn(boto_session, dns_name):
    """Fetch and return the latest certificate matching dns name"""
    log = logging.getLogger(__name__)
    acm = boto_session.client("acm")

    certicate = _search_certificate(acm, dns_name, CertificateStatuses=["ISSUED"])
    if certicate:
        log.info("Found ISSUED certificate %s for %s", certicate, dns_name)
        return certicate

    certicate = _search_certificate(acm, dns_name, CertificateStatuses=["PENDING_VALIDATION"])
    if certicate:
        _validate_certificate_with_retry(boto_session, dns_name, certicate)

        # Warn that certificate is in pending state, so https will not work until certificate is
        # in issued state and project is redeployed
        log.warning(
            f"Certificate {certicate} for your namespace is not in issued state yet, so"
            " https will not work. Please redeploy your project later with the --init flag"
            " set to enable https."
        )
        # Return empty string so that load balancer will create, and at least http will work
        return ""

    # No cert found
    return None

def new_certificate_arn(boto_session, dns_name):
    """Ask for a new certificate"""
    log = logging.getLogger(__name__)
    acm = boto_session.client("acm")

    validation_dns = ".".join(dns_name.split(".")[-2:])
    token = re.sub("\W", "_", dns_name)  # Dns name that match r'\w+'

    log.info("Requesting a new certificate %s", dns_name)
    arn = acm.request_certificate(
        ValidationMethod="DNS",
        DomainName=dns_name,
        # SubjectAlternativeNames=[],  # One domain name per certificate simplifies things
        IdempotencyToken=md5(token.encode()).hexdigest(),
        DomainValidationOptions=[
            dict(
                DomainName=dns_name,
                # Only get the main domain (last 2 elements)
                ValidationDomain=validation_dns,
            )
        ],  # leave the default there
    )["CertificateArn"]

    _validate_certificate_with_retry(boto_session, dns_name, arn)

    # Warn that certificate is in pending state yet, so https will not work until certificate is
    # in issued state and project is redeployed
    log.warning(
        f"Certificate {arn} for your namespace is not in issued state yet, so"
        " https will not work.  Please redeploy your project later with the --init flag"
        " set to enable https."
    )
    # Return empty string so that load balancer will create, and at least http will work
    return ""


def _validate_certificate_with_retry(boto_session, dns_name, arn, max_retries=20):
    """Validate new certificate using DNS validation"""
    log = logging.getLogger(__name__)

    # Create the hosted zone for later dns validation
    hostedzone_name = ".".join(dns_name.split(".")[1:])
    hostedzone = get_hostedzone(boto_session, hostedzone_name) or create_hostedzone(
        boto_session, hostedzone_name
    )

    acm = boto_session.client("acm")

    retry_count = 0
    while retry_count < max_retries:
        try:
            cname_info = acm.describe_certificate(CertificateArn=arn)["Certificate"][
                "DomainValidationOptions"
            ][0]["ResourceRecord"]
            cname_record = {cname_info["Name"][:-1]: cname_info["Value"]}
        except (KeyError, IndexError):
            retry_count += 1
        else:
            break
    if retry_count == max_retries:
        log.warning(
            f"Unable to validate certificate {arn} via DNS at this time. Please try again"
            " later by rerunning your aladdin command or by manually validating using the"
            " instructions here:"
            " https://github.com/fivestars/aladdin-fs/blob/master/doc/dns_and_certificate.md."
        )
    else:
        fill_dns_dict(boto_session, hostedzone, cname_record)


def _search_certificate(client, domain_name, **filters):
    paginator = client.get_paginator("list_certificates")

    for page in paginator.paginate(**filters):
        for cert in page["CertificateSummaryList"]:
            if cert["DomainName"] == domain_name:
                return cert["CertificateArn"]
