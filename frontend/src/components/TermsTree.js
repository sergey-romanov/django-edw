import { connect } from 'react-redux';
import { bindActionCreators } from 'redux';
import React, { Component } from 'react';
import * as TermsTreeActions from '../actions/TermsTreeActions';
import TermsTreeItem from './TermsTreeItem';


class TermsTree extends Component {
  componentDidMount() {
    this.props.actions.loadTree();
  }

  componentWillReceiveProps(nextProps) {
    const req_curr = this.props.terms.requested,
          req_next = nextProps.terms.requested;
    if (req_curr != req_next) {
      this.props.actions.reloadTree(req_next.array);
    }
  }

  render() {
    const { terms, actions } = this.props,
          term = terms.tree.root,
          tagged = terms.tagged,
          expanded = terms.expanded,
          info_expanded = terms.info_expanded;

    let tree = "";
    if ( !!term ) {
      tree = (
        <TermsTreeItem key={term.id}
                       term={term}
                       tagged={tagged}
                       expanded={expanded}
                       info_expanded={info_expanded}
                       actions={actions}/>
      );
    }
    return (
      <div className="terms-tree-container">
        <ul className="terms-tree">
          {tree}
        </ul>
      </div>
    )
  }
}


function mapState(state) {
  return {
    terms: state.terms,
  };
}


function mapDispatch(dispatch) {
  return {
    actions: bindActionCreators(TermsTreeActions, dispatch),
    dispatch: dispatch
  };
}


export default connect(mapState, mapDispatch)(TermsTree);

