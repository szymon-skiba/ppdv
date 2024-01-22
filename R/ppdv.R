# AUTO GENERATED FILE - DO NOT EDIT

#' @export
ppdv <- function(id=NULL, sensorData=NULL) {
    
    props <- list(id=id, sensorData=sensorData)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'Ppdv',
        namespace = 'ppdv',
        propNames = c('id', 'sensorData'),
        package = 'ppdv'
        )

    structure(component, class = c('dash_component', 'list'))
}
