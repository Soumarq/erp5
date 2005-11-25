##############################################################################
#
# Copyright (c) 2002, 2005 Nexedi SARL and Contributors. All Rights Reserved.
#                    Sebastien Robin <seb@nexedi.com>
#                    Yoshinori Okuji <yo@nexedi.com>
#                    Romain Courteaud <romain@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

"""
Define in this class all classes intended to group every kind of movement
"""

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, DTMLFile
from zLOG import LOG
from Products.PythonScripts.Utility import allow_class

class RootMovementGroup:

  def __init__(self, class_list, movement=None, last_line_class_name=None,
               separate_method_name_list=[]):
    self._nested_class = None
    self.setNestedClass(class_list=class_list)
    self._movement_list = []
    self._group_list = []

    self._class_list = class_list
    self._last_line_class_name = last_line_class_name
    self._separate_method_name_list = separate_method_name_list

    if movement is not None :
      self.append(movement)

  def getNestedClass(self, class_list):
    if len(class_list)>0:
      return class_list[0]
    return None

  def setNestedClass(self,class_list):
    """
      This sets an appropriate nested class.
    """
    self._nested_class = self.getNestedClass(class_list)

  def _appendGroup(self, movement):
    nested_instance = self._nested_class(
                    movement=movement,
                    class_list=self._class_list[1:],
                    last_line_class_name=self._last_line_class_name,
                    separate_method_name_list=self._separate_method_name_list)
    self._group_list.append(nested_instance)

  def append(self, movement):
    is_movement_in_group = 0
    for group in self.getGroupList():
      if group.test(movement) :
        try:
          group.append(movement)
          is_movement_in_group = 1
          break
        except "MovementRejected":
          if self.__class__.__name__ == self._last_line_class_name:
            pass
          else:
            raise "MovementRejected"
    if is_movement_in_group == 0 :
      if self._nested_class is not None:
        self._appendGroup(movement)
      else:
        # We are on a node group
        movement_list = self.getMovementList()
        if len(movement_list) > 0:
          # We have a conflict here, because it is forbidden to have 
          # 2 movements on the same node group
          tmp_result = self._separate(movement)
          self._movement_list, split_movement_list = tmp_result
          if split_movement_list != [None]:
            # We rejected a movement, we need to put it on another line
            # Or to create a new one
            raise "MovementRejected"
        else:
          # No movement on this node, we can add it
          self._movement_list.append(movement)

  def getGroupList(self):
    return self._group_list

  def setGroupEdit(self, **kw):
    """
      Store properties for the futur created object 
    """
    self._property_dict = kw

  def getGroupEditDict(self):
    """
      Get property dict for the futur created object 
    """
    if hasattr(self, '_property_dict'):
      return self._property_dict
    else:
      return {}

  def getMovementList(self):
    """
      Return movement list in the current group
    """
    movement_list = []
    group_list = self.getGroupList()
    if len(group_list) == 0:
      return self._movement_list
    else:
      for group in group_list:
        movement_list.extend(group.getMovementList())
      return movement_list

  def _separate(self, movement):
    """
      Separate 2 movements on a node group
    """
    movement_list = self.getMovementList()
    if len(movement_list) != 1:
      raise "ProgrammingError", "Can separate only 2 movements"
    else:
      old_movement = self.getMovementList()[0]

      new_stored_movement = old_movement
      added_movement = movement
      rejected_movement = None

      for separate_method_name in self._separate_method_name_list:
        method = getattr(self, separate_method_name)

        new_stored_movement,\
        rejected_movement= method(new_stored_movement,
                                  added_movement=added_movement)
        if rejected_movement is None:
          added_movement = None
        else:
          break
        
      return [new_stored_movement], [rejected_movement]

  ########################################################
  # Separate methods
  ########################################################
  def _genericCalculation(self, movement, added_movement=None):
    """ Generic creation of FakeMovement
    """
    if added_movement is not None:
      # Create a fake movement
      new_movement = FakeMovement([movement, added_movement])
    else:
      new_movement = movement
    return new_movement

  def calculateAveragePrice(self, movement, added_movement=None):
    """ Create a new movement with a average price
    """
    new_movement = self._genericCalculation(movement,
                                            added_movement=added_movement)
    new_movement.setPriceMethod("getAveragePrice")
    return new_movement, None

  def calculateSeparatePrice(self, movement, added_movement=None):
    """ Separate movement which have the same price
    """
    if added_movement is not None and \
            movement.getPrice() == added_movement.getPrice() :
      new_movement = self._genericCalculation(movement,
                                              added_movement=added_movement)
      new_movement.setPriceMethod('getAddQuantity')
      return new_movement, None
    return movement, added_movement

  def calculateAddQuantity(self, movement, added_movement=None):
    """ Create a new movement with the sum of quantity
    """
    new_movement = self._genericCalculation(movement,
                                            added_movement=added_movement)
    new_movement.setQuantityMethod("getAddQuantity")
    return new_movement, None

allow_class(RootMovementGroup)

class OrderMovementGroup(RootMovementGroup):
  """ Group movements that comes from the same Order. """
  def __init__(self,movement, **kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    if hasattr(movement, 'getRootAppliedRule'):
      # This is a simulation movement
      order_value = movement.getRootAppliedRule().getCausalityValue(
                              portal_type=movement.getPortalOrderTypeList())
      if order_value is None:
        # In some cases (ex. DeliveryRule), there is no order
        # we may consider a PackingList as the order in the OrderGroup
        order_value = movement.getRootAppliedRule().getCausalityValue(
                        portal_type=movement.getPortalDeliveryTypeList())
    else:
      # This is a temp movement
      order_value = None
    if order_value is None:
      order_relative_url = None
    else:
      # get the id of the enclosing delivery
      # for this cell or line
      order_relative_url = order_value.getRelativeUrl()
    self.order = order_relative_url
    self.setGroupEdit(causality_value=order_value)

  def test(self,movement):
    if hasattr(movement, 'getRootAppliedRule'):
      order_value = movement.getRootAppliedRule().getCausalityValue(
                        portal_type=movement.getPortalOrderTypeList())

      if order_value is None:
        # In some cases (ex. DeliveryRule), there is no order
        # we may consider a PackingList as the order in the OrderGroup
        order_value = movement.getRootAppliedRule().getCausalityValue(
                        portal_type=movement.getPortalDeliveryTypeList())
    else:
      # This is a temp movement
      order_value = None
    if order_value is None:
      order_relative_url = None
    else:
      # get the id of the enclosing delivery
      # for this cell or line
      order_relative_url = order_value.getRelativeUrl()
    if order_relative_url == self.order:
      return 1
    else :
      return 0

allow_class(OrderMovementGroup)


class CausalityMovementGroup(RootMovementGroup):
  """ Groups movement that comes from simulation movement that shares the
  same explanation relation. For example, it groups in an Invoice
  movements from the same Packing List. """
  
  def __init__(self, movement, **kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    explanation_relative_url = self._getExplanationRelativeUrl(movement)
    self.explanation = explanation_relative_url

  def _getExplanationRelativeUrl(self, movement):
    """ Get the order value for a movement """
    if hasattr(movement, 'getParent'):
      # This is a simulation movement
      if movement.getParent() != movement.getRootAppliedRule() :
        # get the explanation of parent movement if we have not been
        # created by the root applied rule.
        movement = movement.getParent().getParent()
      explanation_value = movement.getExplanationValue()
      if explanation_value is None:
        raise ValueError, 'No explanation for movement %s' % movement.getPath()
    else:
      # This is a temp movement
      explanation_value = None
    if explanation_value is None:
      explanation_relative_url = None
    else:
      # get the enclosing delivery for this cell or line
      if hasattr(explanation_value, 'getExplanationValue') :
        explanation_value = explanation_value.getExplanationValue()
        
      explanation_relative_url = explanation_value.getRelativeUrl()
    return explanation_relative_url
    
  def test(self,movement):
    return self._getExplanationRelativeUrl(movement) == self.explanation
    
allow_class(CausalityMovementGroup)


class PathMovementGroup(RootMovementGroup):
  """ Group movements that have the same source and the same destination."""
  def __init__(self, movement, **kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.source = movement.getSource()
    self.destination = movement.getDestination()

    self.setGroupEdit(
        source_value=movement.getSourceValue(),
        destination_value=movement.getDestinationValue(),
    )

  def test(self, movement):
    return movement.getSource() == self.source and \
      movement.getDestination() == self.destination

allow_class(PathMovementGroup)

class SectionPathMovementGroup(RootMovementGroup):
  """ Groups movement that have the same source_section and
  destination_section."""
  def __init__(self, movement, **kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.source_section = movement.getSourceSection()
    self.destination_section = movement.getDestinationSection()
    self.setGroupEdit(
        source_section = movement.getSourceSection(),
        destination_section = movement.getDestinationSection(),
    )

  def test(self, movement):
    return movement.getSourceSection() == self.source_section and \
       movement.getDestinationSection() == self.destination_section

allow_class(SectionPathMovementGroup)

# XXX Naming issue ?
class QuantitySignMovementGroup(RootMovementGroup):
  def __init__(self, movement, **kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    quantity = movement.getQuantity()
    if quantity == 0:
      self.sign = 0
    elif quantity > 0:
      self.sign = 1
    else:
      self.sign = -1
    self.setGroupEdit(quantity_sign=self.sign)

  def test(self, movement):
    quantity = movement.getQuantity()
    if quantity == 0 or self.sign == 0 :
      return 1
    if quantity > 0:
      sign = 1
    else:
      sign = -1
    return self.sign == sign

allow_class(QuantitySignMovementGroup)

class DateMovementGroup(RootMovementGroup):

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.start_date = movement.getStartDate()
    self.stop_date = movement.getStopDate()
    self.setGroupEdit(
        start_date=movement.getStartDate(),
        stop_date=movement.getStopDate()
    )

  def test(self,movement):
    if movement.getStartDate() == self.start_date and \
      movement.getStopDate() == self.stop_date :
      return 1
    else :
      return 0

allow_class(DateMovementGroup)

class CriterionMovementGroup(RootMovementGroup):

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    if hasattr(movement, 'getGroupCriterion'):
      self.criterion = movement.getGroupCriterion()
    else:
      self.criterion = None

  def test(self,movement):
    # we must have the same criterion
    if hasattr(movement, 'getGroupCriterion'):
      criterion = movement.getGroupCriterion()
    else:
      criterion = None
    return self.criterion == criterion

allow_class(CriterionMovementGroup)

class ResourceMovementGroup(RootMovementGroup):

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.resource = movement.getResource()
    self.setGroupEdit(
        resource_value=movement.getResourceValue()
    )

  def test(self,movement):
    if movement.getResource() == self.resource :
      return 1
    else :
      return 0

allow_class(ResourceMovementGroup)

class BaseVariantMovementGroup(RootMovementGroup):

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.base_category_list = movement.getVariationBaseCategoryList()
    if self.base_category_list is None:
      #LOG('BaseVariantGroup __init__', 0, 'movement = %s, movement.showDict() = %s' % (repr(movement), repr(movement.showDict())))
      self.base_category_list = []

  def test(self,movement):
    # we must have the same number of categories
    categories_identity = 0
    #LOG('BaseVariantGroup', 0, 'self.base_category_list = %s, movement = %s, movement.getVariationBaseCategoryList() = %s' % (repr(self.base_category_list), repr(movement), repr(movement.getVariationBaseCategoryList())))
    movement_base_category_list = movement.getVariationBaseCategoryList()
    if movement_base_category_list is None:
      #LOG('BaseVariantGroup test', 0, 'movement = %s, movement.showDict() = %s' % (repr(movement), repr(movement.showDict())))
      movement_base_category_list = []
    if len(self.base_category_list) == len(movement_base_category_list):
      for category in movement_base_category_list:
        if not category in self.base_category_list :
          break
      else :
        categories_identity = 1
    return categories_identity

allow_class(BaseVariantMovementGroup)

class VariantMovementGroup(RootMovementGroup):

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.category_list = movement.getVariationCategoryList()
    if self.category_list is None:
      #LOG('VariantGroup __init__', 0, 'movement = %s, movement.showDict() = %s' % (repr(movement), repr(movement.showDict())))
      self.category_list = []
    self.setGroupEdit(
        variation_category_list=self.category_list
    )

  def test(self,movement):
    # we must have the same number of categories
    categories_identity = 0
    movement_category_list = movement.getVariationCategoryList()
    if movement_category_list is None:
      #LOG('VariantGroup test', 0, 'movement = %s, movement.showDict() = %s' % (repr(movement), repr(movement.showDict())))
      movement_category_list = []
    if len(self.category_list) == len(movement_category_list):
      for category in movement_category_list:
        if not category in self.category_list :
          break
      else :
        categories_identity = 1
    return categories_identity

allow_class(VariantMovementGroup)

from copy import copy

class CategoryMovementGroup(RootMovementGroup):  
  """
    This seems to be a useless class
  """
  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.category_list = list(movement.getCategoryList())
    if self.category_list is None:
      self.category_list = []
    self.category_list.sort()

  def test(self,movement):
    # we must have the same number of categories
    movement_category_list = list(movement.getCategoryList())
    if movement_category_list is None:
      movement_category_list = []
    movement_category_list.sort()
    if self.category_list == movement_category_list:
      return 1
    return 0

allow_class(CategoryMovementGroup)

class OptionMovementGroup(RootMovementGroup):

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    option_base_category_list = movement.getPortalOptionBaseCategoryList()
    self.option_category_list = movement.getVariationCategoryList(base_category_list=option_base_category_list)
    #LOG('OptionMovementGroup.__init__, option_category_list',0,self.option_category_list)
    if self.option_category_list is None:
      self.option_category_list = []
    # XXX This is very bad, but no choice today.
    self.setGroupEdit(industrial_phase_list = self.option_category_list)

  def test(self,movement):
    # we must have the same number of categories
    categories_identity = 0
    option_base_category_list = movement.getPortalOptionBaseCategoryList()
    movement_option_category_list = movement.getVariationCategoryList(base_category_list=option_base_category_list)
    #LOG('OptionMovementGroup.test, option_category_list',0,movement_option_category_list)
    if movement_option_category_list is None:
      movement_option_category_list = []
    if len(self.option_category_list) == len(movement_option_category_list):
      categories_identity = 1
      for category in movement_option_category_list:
        if not category in self.option_category_list :
          categories_identity = 0
          break
    return categories_identity

allow_class(OptionMovementGroup)

class VariationPropertyMovementGroup(RootMovementGroup):
  """
  Compare variation property dict of movement.
  """

  def __init__(self, movement, **kw):
    """
    Store variation property dict of the first movement.
    """
    RootMovementGroup.__init__(self, movement=movement, **kw)
    self.property_dict = movement.getVariationPropertyDict()
    self.setGroupEdit(
      variation_property_dict = self.property_dict
    )

  def test(self, movement):
    """
    Check if the movement can be inserted in the group.
    """
    identity = 0
    variation_property_dict = movement.getVariationPropertyDict()
    variation_property_list = variation_property_dict.keys()
    if len(variation_property_list) == len(self.property_dict):
      # Same number of property. Good point.
      for variation_property in variation_property_list:
        try:
          if variation_property_dict[variation_property] != \
              self.property_dict[variation_property]:
            # Value is not the same for both movements
            break
        except KeyError:
          # Key is not common to both movements
          break
      else:
        identity = 1
    return identity

allow_class(VariationPropertyMovementGroup)

class FakeMovement:
  """
    A fake movement which simulate some methods on a movement needed 
    by DeliveryBuilder.
    It contents a list a real ERP5 Movement and can modify them.
  """
  def __init__(self, movement_list):
    """
      Create a fake movement and store the list of real movement
    """
    self.__price_method = None
    self.__quantity_method = None
    self.__movement_list = []
    for movement in movement_list:
      self.append(movement)
    # This object must not be use when there is not 2 or more movements
    if len(movement_list) < 2:
      raise "ProgrammingError", "FakeMovement used where it does not."
    # All movements must share the same getVariationCategoryList
    # So, verify and raise a error if not
    # But, if DeliveryBuilder is well configured, this can never append ;)
    reference_variation_category_list = movement_list[0].\
                                           getVariationCategoryList()
    error_raising_needed = 0
    for movement in movement_list[1:]:
      variation_category_list = movement.getVariationCategoryList()
      if len(variation_category_list) !=\
         len(reference_variation_category_list):
        error_raising_needed = 1
        break

      for variation_category in variation_category_list:
        if variation_category not in reference_variation_category_list:
          error_raising_needed = 1
          break
    
    if error_raising_needed == 1:
      raise "ProgrammingError", "FakeMovement not well used."

  def append(self, movement):
    """
      Append movement to the movement list
    """
    if movement.__class__.__name__ == "FakeMovement":
      self.__movement_list.extend(movement.getMovementList())
      self.__price_method = movement.__price_method
      self.__quantity_method = movement.__quantity_method
    else:
      self.__movement_list.append(movement)

  def getMovementList(self):
    """
      Return content movement list
    """
    return self.__movement_list
    
  def setDeliveryValue(self, object):
    """
      Set Delivery value for each movement
    """
    for movement in self.__movement_list:
      movement.edit(delivery_value=object)

  def getDeliveryValue(self):
    """
      Only use to test if all movement are not linked (if user did not
      configure DeliveryBuilder well...).
      Be careful.
    """
    result = None
    for movement in self.__movement_list:
      mvt_delivery = movement.getDeliveryValue()
      if mvt_delivery is not None:
        result = mvt_delivery
        break
    return result

  def getRelativeUrl(self):
    """
      Only use to return a short description of one movement 
      (if user did not configure DeliveryBuilder well...).
      Be careful.
    """
    return self.__movement_list[0].getRelativeUrl()

  def setDeliveryRatio(self, delivery_ratio):
    """
      Calculate delivery_ratio
    """
    total_quantity = 0
    for movement in self.__movement_list:
      total_quantity += movement.getQuantity()

    if total_quantity != 0:
      for movement in self.__movement_list:
        quantity = movement.getQuantity()
        movement.edit(delivery_ratio=quantity*delivery_ratio/total_quantity)
    else:
      # Distribute equally ratio to all movement
      mvt_ratio = 1 / len(self.__movement_list)
      for movement in self.__movement_list:
        movement.edit(delivery_ratio=mvt_ratio)
      
  def getPrice(self):
    """
      Return calculated price
    """
    if self.__price_method is not None:
      return getattr(self, self.__price_method)()
    else:
      return None
  
  def setPriceMethod(self, method):
    """
      Set the price method
    """
    self.__price_method = method

  def getQuantity(self):
    """
      Return calculated quantity
    """
    return getattr(self, self.__quantity_method)()
 
  def setQuantityMethod(self, method):
    """
      Set the quantity method
    """
    self.__quantity_method = method

  def getAveragePrice(self):
    """
      Return average price 
    """
    return (self.getAddPrice() / self.getAddQuantity())

  def getAddQuantity(self):
    """
      Return the total quantity
    """
    total_quantity = 0
    for movement in self.getMovementList():
      total_quantity += movement.getQuantity()
    return total_quantity

  def getAddPrice(self):
    """
      Return total price 
    """
    total_price = 0
    for movement in self.getMovementList():
      total_price += (movement.getQuantity() * movement.getPrice())
    return total_price

  def recursiveReindexObject(self):
    """
      Reindex all movements
    """
    for movement in self.getMovementList():
      movement.recursiveReindexObject()

  def immediateReindexObject(self):
    """
      Reindex immediately all movements
    """
    for movement in self.getMovementList():
      movement.immediateReindexObject()

  def getPath(self):
    """
      Return the movements path list
    """
    path_list = []
    for movement in self.getMovementList():
      path_list.append(movement.getPath())
    return path_list

  def getVariationBaseCategoryList(self, omit_option_base_category=0,**kw):
    """
      Return variation base category list
      Which must be shared by all movement
    """
    return self.__movement_list[0].getVariationBaseCategoryList(
                      omit_option_base_category=omit_option_base_category,**kw)

  def getVariationCategoryList(self, omit_option_base_category=0,**kw):
    """
      Return variation base category list
      Which must be shared by all movement
    """
    return self.__movement_list[0].getVariationCategoryList(
                      omit_option_base_category=omit_option_base_category,**kw)

  def edit(self, **kw):
    """
      Written in order to call edit in delivery builder,
      as it is the generic way to modify object.
    """
    for key in kw.keys():
      if key == 'delivery_ratio':
        self.setDeliveryRatio(kw[key])
      elif key == 'delivery_value':
        self.setDeliveryValue(kw[key])
      else:
        raise "FakeMovementError",\
              "Could not call edit on Fakeovement with parameters: %r" % key

# XXX This should not be here
# I (seb) have commited this because movement groups are not
# yet configurable through the zope web interface
class IntIndexMovementGroup(RootMovementGroup):

  def getIntIndex(self,movement):
    order_value = movement.getOrderValue()
    int_index = 0
    if order_value is not None:
      if "Line" in order_value.getPortalType():
        int_index = order_value.getIntIndex()
      elif "Cell" in order_value.getPortalType():
        int_index = order_value.getParentValue().getIntIndex()
    return int_index

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    int_index = self.getIntIndex(movement)
    self.int_index = int_index
    self.setGroupEdit(
        int_index=int_index
    )

  def test(self,movement):
    if self.getIntIndex(movement) == self.int_index :
      return 1
    else :
      return 0

allow_class(IntIndexMovementGroup)

# XXX This should not be here
# I (seb) have commited this because movement groups are not
# yet configurable through the zope web interface
class DecisionMovementGroup(RootMovementGroup):

  def getDecision(self,movement):
    return movement.getDecision()

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    decision = self.getDecision(movement)
    self.decision = decision
    self.setGroupEdit(
        decision=decision
    )

  def test(self,movement):
    if self.getDecision(movement) == self.decision :
      return 1
    else :
      return 0

allow_class(DecisionMovementGroup)

# XXX This should not be here
# I (seb) have commited this because movement groups are not
# yet configurable through the zope web interface
class BrandMovementGroup(RootMovementGroup):

  def getBrand(self,movement):
    return movement.getBrand()

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    brand = self.getBrand(movement)
    self.brand = brand
    self.setGroupEdit(
        brand=brand
    )

  def test(self,movement):
    if self.getBrand(movement) == self.brand :
      return 1
    else :
      return 0

allow_class(BrandMovementGroup)

class AggregateMovementGroup(RootMovementGroup):

  def getAggregateList(self,movement):
    aggregate_list = movement.getAggregateList()
    aggregate_list.sort()
    return aggregate_list

  def __init__(self,movement,**kw):
    RootMovementGroup.__init__(self, movement=movement, **kw)
    aggregate = self.getAggregateList(movement)
    self.aggregate = aggregate
    self.setGroupEdit(
        aggregate=aggregate
    )

  def test(self,movement):
    if self.getAggregate(movement) == self.aggregate :
      return 1
    else :
      return 0

allow_class(BrandMovementGroup)
