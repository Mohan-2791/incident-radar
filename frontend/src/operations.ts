import { graphql } from "./gql";

// Every operation lives here. `npm run codegen` turns these into fully typed documents,
// so components get typed `data`, `variables`, and enums with no hand-written interfaces.

export const IncidentFields = graphql(`
  fragment IncidentFields on IncidentType {
    id
    title
    severity
    status
    createdAt
    resolvedAt
    durationMinutes
    service {
      id
      name
    }
  }
`);

export const StatsQuery = graphql(`
  query Stats {
    stats {
      openTotal
      resolvedLast30Days
      meanMinutesToResolve
      openBySeverity {
        severity
        count
      }
    }
  }
`);

export const ServicesQuery = graphql(`
  query Services {
    services {
      id
      name
      tier
      ownerTeam
      openIncidentCount
    }
  }
`);

export const IncidentsQuery = graphql(`
  query Incidents($filter: IncidentFilter, $after: String) {
    incidents(filter: $filter, first: 12, after: $after) {
      totalCount
      pageInfo {
        hasNextPage
        endCursor
      }
      edges {
        cursor
        node {
          ...IncidentFields
        }
      }
    }
  }
`);

export const IncidentQuery = graphql(`
  query Incident($id: ID!) {
    incident(id: $id) {
      ...IncidentFields
      service {
        ownerTeam
        tier
      }
      updates {
        id
        message
        status
        createdAt
      }
    }
  }
`);

export const OpenIncidentMutation = graphql(`
  mutation OpenIncident($input: OpenIncidentInput!) {
    openIncident(input: $input) {
      __typename
      ... on IncidentType {
        id
      }
      ... on UserError {
        field
        message
      }
    }
  }
`);

export const PostUpdateMutation = graphql(`
  mutation PostUpdate($input: PostUpdateInput!) {
    postUpdate(input: $input) {
      __typename
      ... on IncidentType {
        id
      }
      ... on UserError {
        field
        message
      }
    }
  }
`);

export const IncidentChangedSubscription = graphql(`
  subscription IncidentChanged {
    incidentChanged {
      id
      title
      status
    }
  }
`);
