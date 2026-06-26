ARG MAGIC_LINK_VERSION=0.26

FROM alpine AS downloader
ARG MAGIC_LINK_VERSION
RUN wget -q \
    "https://repo1.maven.org/maven2/io/phasetwo/keycloak/keycloak-magic-link/${MAGIC_LINK_VERSION}/keycloak-magic-link-${MAGIC_LINK_VERSION}.jar" \
    -O /keycloak-magic-link.jar

FROM quay.io/keycloak/keycloak:24.0
COPY --from=downloader /keycloak-magic-link.jar /opt/keycloak/providers/keycloak-magic-link.jar
