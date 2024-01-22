import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Feet from '../../public/images/150216.svg'
/**
 * ExampleComponent is an example component.
 * It takes a property, `label`, and
 * displays it.
 * It renders an input with the property `value`
 * which is editable by the user.
 */
const Ppdv = (props) => {
    const { id, sensorData } = props;

    const sensorPositions = {
        'L0': { x: 110, y: 175 },   
        'L1': { x: 40, y: 210 },   
        'L2': { x: 75, y: 400 },   
        'R0': { x: 190, y: 175 },  
        'R1': { x: 260, y: 210 },  
        'R2': { x: 225, y: 400 }, 
    };

    const getColorForValue = (value) => {
        const maxPressureValue = 1100;

        value = Math.min(value, maxPressureValue);

        const ratio = value / maxPressureValue;

        const hue = ((1 - ratio) * 120).toString(10);
        return `hsl(${hue}, 100%, 50%)`; 
    };

    const gradientId = "pressure-gradient";


    return (
        <div id={id}>
            {/* SVG container for the feet image and pressure points */}
            <svg width="300px" height="550px" viewBox="0 0 300 550">
                <defs>
                    <linearGradient id={gradientId} x1="0%" y1="100%" x2="100%" y2="100%">
                        <stop offset="0%" style={{ stopColor: "green", stopOpacity: 1 }} />
                        <stop offset="100%" style={{ stopColor: "red", stopOpacity: 1 }} />
                    </linearGradient>
                </defs>
                <image href={Feet} x="0" y="0" width="300px" height="500px" />
                {sensorData.map((sensor) => {
                    const position = sensorPositions[sensor.name];
                    const color = getColorForValue(sensor.value);
                    return (
                        <g key={sensor.id}>
                            <circle cx={position.x} cy={position.y} r="17" fill={color} />
                            <text x={position.x} y={position.y - 20} textAnchor="middle" fill="white" fontSize="15" fontWeight="bold">
                                {sensor.value}
                            </text>
                            <text x={position.x} y={position.y+5} textAnchor="middle" fill="white" fontSize="13" fontWeight="bold">
                                {sensor.name}
                            </text>
                        </g>
                    );
                })}
                <rect x="40" y="500" width="200" height="20" fill={`url(#${gradientId})`} />
                <text x="40" y="540" fontSize="17" fill="#000">Low [0]</text>
                <text x="250" y="540" fontSize="17" fill="#000" textAnchor="end">High [1100+]</text>
            </svg>
        </div>
    );
}

Ppdv.defaultProps = {
    sensorData: []
};

Ppdv.propTypes = {
    id: PropTypes.string,
    sensorData: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
    }))
};

export default Ppdv;